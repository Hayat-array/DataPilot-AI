"""
CoderAgent — Schema-aware Python/Pandas code generator.
Uses Groq (LLaMA-3) if GROQ_API_KEY is set, falls back to
a rich template engine that covers all 5 project use-cases.
"""

import os
import re
import json
import textwrap
from app.agents.base import BaseAgent


GROQ_MODEL = "llama-3.1-70b-versatile"   # active LLaMA-3.1 model on Groq

# ── System prompt for the LLM ──────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are an expert Python data scientist. Given a user question and a dataset schema,
write COMPLETE, RUNNABLE Python code that:
1. Loads the dataset from the provided file path.
2. Performs the analysis or visualization requested.
3. For any chart/plot: saves it as a PNG file to the given output path using
   plt.savefig(output_path, dpi=300, bbox_inches='tight') and then calls plt.close().
4. Prints a short plain-English insight summary at the end (print statements only).
5. Does NOT use plt.show() — saves to file instead.
6. Handles missing values gracefully (dropna or fillna where appropriate).
7. Uses matplotlib, seaborn, pandas, and numpy only — no external libraries.

Respond with ONLY the Python code block, no explanation. Start directly with `import`.
"""

# ── Intent → template mapping ──────────────────────────────────────────────
INTENT_TEMPLATES = {
    "summary":  "descriptive_summary",
    "describe": "descriptive_summary",
    "profile":  "descriptive_summary",
    "statistic":"descriptive_summary",

    "missing":  "data_quality",
    "null":     "data_quality",
    "clean":    "data_quality",
    "duplicat": "data_quality",
    "quality":  "data_quality",
    "audit":    "data_quality",

    "trend":    "trend_analysis",
    "time":     "trend_analysis",
    "growth":   "trend_analysis",
    "series":   "trend_analysis",

    "cohort":   "cohort_analysis",
    "segment":  "cohort_analysis",
    "group":    "cohort_analysis",
    "cluster":  "cohort_analysis",

    "rank":     "row_retrieval",
    "person":   "row_retrieval",
    "candidate":"row_retrieval",
    "student":  "row_retrieval",
    "row":      "row_retrieval",
    "index":    "row_retrieval",

    "bar":      "bar_chart",
    "pie":      "pie_chart",
    "scatter":  "scatter_plot",
    "histogra": "histogram",
    "distribut":"histogram",
    "heatmap":  "correlation_heatmap",
    "correlat": "correlation_heatmap",
    "plot":     "auto_plot",
    "chart":    "auto_plot",
    "visual":   "auto_plot",
    "graph":    "auto_plot",
}


class CoderAgent(BaseAgent):
    """Schema-aware code generator. Uses Groq LLM when available,
    falls back to a rich template engine for all 5 use-cases."""

    def __init__(self):
        super().__init__("Coder", "Generates Python analytics and visualization scripts.")
        self._groq_client = None
        self._init_groq()

    # ── Groq initialization ────────────────────────────────────────────────
    def _init_groq(self):
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            return
        try:
            from groq import Groq
            self._groq_client = Groq(api_key=api_key)
            self.log_step("groq_ready", "Groq LLM client initialized.")
        except Exception as e:
            self.log_step("groq_init_failed", f"Groq init failed: {e}. Using template fallback.")

    # ── Public API ─────────────────────────────────────────────────────────
    def execute(self, dataset_path: str, user_message: str,
                schema: dict, output_chart_path: str) -> str:
        """
        Generate executable Python code for the given task.

        Args:
            dataset_path:      Absolute path to the uploaded dataset file.
            user_message:      Raw user question / instruction.
            schema:            Dict with keys 'columns', 'dtypes', 'numeric_cols',
                               'categorical_cols', 'shape', 'nulls'.
            output_chart_path: Where the chart PNG should be saved (may be None
                               for text-only tasks).
        Returns:
            Python code string.
        """
        self.log_step("code_gen_start",
                      f"Generating code for: '{user_message[:60]}...' on {os.path.basename(dataset_path)}")

        if self._groq_client:
            code = self._generate_via_groq(dataset_path, user_message, schema, output_chart_path)
            if code:
                self.log_step("code_gen_llm", "Code generated via Groq LLM.")
                return code
            self.log_step("code_gen_fallback", "Groq returned empty — falling back to template.")

        code = self._generate_via_template(dataset_path, user_message, schema, output_chart_path)
        self.log_step("code_gen_template", "Code generated via template engine.")
        return code

    # ── LLM path ──────────────────────────────────────────────────────────
    def _generate_via_groq(self, dataset_path, user_message, schema, output_chart_path):
        schema_str = json.dumps(schema, indent=2, default=str)
        user_prompt = f"""
Dataset file path: {dataset_path}
Output chart path: {output_chart_path or 'NOT_REQUIRED'}
Dataset schema:
{schema_str}

User request: {user_message}

Write complete Python code to fulfill this request. Use the exact file path above.
"""
        try:
            resp = self._groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=1800,
            )
            raw = resp.choices[0].message.content.strip()
            # Strip markdown code fences if present
            code = re.sub(r"^```python\n?", "", raw)
            code = re.sub(r"\n?```$", "", code)
            return code.strip()
        except Exception as e:
            self.log_step("groq_error", str(e))
            return ""

    # ── Template path ──────────────────────────────────────────────────────
    def _classify_intent(self, message: str) -> str:
        msg = message.lower()
        for keyword, intent in INTENT_TEMPLATES.items():
            if keyword in msg:
                return intent
        return "descriptive_summary"

    def _detect_columns(self, message: str, schema: dict):
        """Find column names mentioned in the user message."""
        msg = message.lower()
        cols = schema.get("columns", [])
        mentioned = [c for c in cols if c.lower() in msg]
        numeric = schema.get("numeric_cols", [])
        categorical = schema.get("categorical_cols", [])
        x_col = mentioned[0] if mentioned else (categorical[0] if categorical else cols[0] if cols else "column")
        y_col = mentioned[1] if len(mentioned) > 1 else (numeric[0] if numeric else None)
        return x_col, y_col

    def _loader_snippet(self, dataset_path: str) -> str:
        ext = os.path.splitext(dataset_path)[1].lower()
        if ext == ".csv":
            return f'df = pd.read_csv(r"{dataset_path}")'
        elif ext in (".xlsx", ".xls"):
            return f'df = pd.read_excel(r"{dataset_path}")'
        else:
            return f'df = pd.read_json(r"{dataset_path}")'

    def _generate_via_template(self, dataset_path, user_message, schema, output_chart_path):
        intent    = self._classify_intent(user_message)
        loader    = self._loader_snippet(dataset_path)
        numeric   = schema.get("numeric_cols", [])
        categ     = schema.get("categorical_cols", [])
        all_cols  = schema.get("columns", [])
        x_col, y_col = self._detect_columns(user_message, schema)

        chart_save = (
            f'plt.savefig(r"{output_chart_path}", dpi=300, bbox_inches="tight", facecolor="white"); plt.close()'
            if output_chart_path else "plt.close()"
        )

        templates = {
            # ── 1. Descriptive Summary ───────────────────────────────────
            "descriptive_summary": f"""\
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

{loader}
df.replace(r'^\\s*$', np.nan, regex=True, inplace=True)

print("=" * 60)
print("DATASET OVERVIEW")
print("=" * 60)
print(f"Shape        : {{df.shape[0]}} rows × {{df.shape[1]}} columns")
print(f"Memory Usage : {{df.memory_usage(deep=True).sum() / 1024:.1f}} KB")
print()

print("COLUMN TYPES & NULLS")
print("-" * 40)
for col in df.columns:
    nulls = df[col].isnull().sum()
    pct   = nulls / len(df) * 100
    print(f"  {{col:<25}} {{str(df[col].dtype):<12}} nulls={{nulls}} ({{pct:.1f}}%)")
print()

numeric_cols = df.select_dtypes(include='number').columns.tolist()
if numeric_cols:
    print("NUMERIC STATISTICS")
    print("-" * 40)
    print(df[numeric_cols].describe().round(3).to_string())
    print()

    # Correlation heatmap
    if len(numeric_cols) >= 2:
        fig, ax = plt.subplots(figsize=(10, 7))
        corr = df[numeric_cols].corr()
        mask = np.triu(np.ones_like(corr, dtype=bool))
        sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="coolwarm",
                    ax=ax, linewidths=0.5, cbar_kws={{"shrink": 0.8}})
        ax.set_title("Feature Correlation Heatmap", fontsize=14, fontweight="bold", pad=15)
        plt.tight_layout()
        {chart_save}
        print("CHART: Correlation heatmap saved.")
print("Summary complete.")
""",
            # ── 2. Data Quality Audit ────────────────────────────────────
            "data_quality": f"""\
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

{loader}
df.replace(r'^\\s*$', np.nan, regex=True, inplace=True)

print("=" * 60)
print("DATA QUALITY AUDIT REPORT")
print("=" * 60)

total_cells = df.shape[0] * df.shape[1]
total_nulls = df.isnull().sum().sum()
completeness = (1 - total_nulls / total_cells) * 100
duplicates   = df.duplicated().sum()

print(f"Total Rows        : {{df.shape[0]}}")
print(f"Total Columns     : {{df.shape[1]}}")
print(f"Total Cells       : {{total_cells}}")
print(f"Missing Cells     : {{total_nulls}} ({{100 - completeness:.1f}}%)")
print(f"Completeness      : {{completeness:.1f}}%")
print(f"Duplicate Rows    : {{duplicates}}")
print()

# Per-column null counts
null_counts = df.isnull().sum()
null_counts = null_counts[null_counts > 0].sort_values(ascending=False)
if not null_counts.empty:
    print("COLUMNS WITH MISSING VALUES:")
    print("-" * 40)
    for col, cnt in null_counts.items():
        pct = cnt / len(df) * 100
        bar = "█" * int(pct / 5)
        print(f"  {{col:<25}} {{cnt:>5}} ({{pct:5.1f}}%) {{bar}}")
    print()

# Visualize missing values
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("Data Quality Audit", fontsize=14, fontweight="bold")

# Null heatmap
sns.heatmap(df.isnull(), cbar=False, cmap="YlOrRd", ax=axes[0], yticklabels=False)
axes[0].set_title("Missing Values Map")

# Bar chart of nulls
if not null_counts.empty:
    null_counts.plot(kind="barh", ax=axes[1], color="#ef4444", edgecolor="white")
    axes[1].set_xlabel("Missing Count")
    axes[1].set_title("Missing Values by Column")
    axes[1].invert_yaxis()
else:
    axes[1].text(0.5, 0.5, "No missing values\\n\\nDataset is 100% complete!",
                 ha="center", va="center", fontsize=14, color="green",
                 transform=axes[1].transAxes)
    axes[1].set_title("Missing Values by Column")

plt.tight_layout()
{chart_save}
print("CHART: Data quality report saved.")
print(f"Overall completeness: {{completeness:.1f}}%")
""",
            # ── 3. Trend Analysis ────────────────────────────────────────
            "trend_analysis": f"""\
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

{loader}

# Detect date-like columns
date_cols  = [c for c in df.columns if any(k in c.lower() for k in ['date','time','month','year','day','period','quarter'])]
numeric_cols = df.select_dtypes(include='number').columns.tolist()

if not date_cols:
    date_cols = [df.columns[0]]

date_col = date_cols[0]
value_col = "{y_col or (numeric_cols[0] if numeric_cols else all_cols[0])}"
if value_col not in df.columns:
    value_col = numeric_cols[0] if numeric_cols else df.columns[1]

try:
    df[date_col] = pd.to_datetime(df[date_col], infer_datetime_format=True, errors='coerce')
    df = df.dropna(subset=[date_col, value_col]).sort_values(date_col)
except Exception:
    pass

print(f"Trend analysis: {{value_col}} over {{date_col}}")
print(f"Date range    : {{df[date_col].min()}} → {{df[date_col].max()}}")
print(f"Data points   : {{len(df)}}")

# Rolling average
if len(df) >= 7:
    window = max(3, len(df) // 10)
    df['rolling_avg'] = df[value_col].rolling(window=window, min_periods=1).mean()

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(df[date_col], df[value_col], alpha=0.4, color="#6366f1", linewidth=1, label="Raw")
if 'rolling_avg' in df.columns:
    ax.plot(df[date_col], df['rolling_avg'], color="#f59e0b", linewidth=2.5, label=f"Rolling avg")
ax.fill_between(df[date_col], df[value_col], alpha=0.08, color="#6366f1")
ax.set_title(f"Trend Analysis: {{value_col}} over time", fontsize=13, fontweight="bold")
ax.set_xlabel(date_col)
ax.set_ylabel(value_col)
ax.legend()
plt.xticks(rotation=30)
plt.tight_layout()
{chart_save}

start_val = df[value_col].iloc[0]
end_val   = df[value_col].iloc[-1]
change    = ((end_val - start_val) / abs(start_val) * 100) if start_val else 0
print(f"Start value : {{start_val:.2f}}")
print(f"End value   : {{end_val:.2f}}")
print(f"Overall change: {{'+' if change > 0 else ''}}{{change:.1f}}%")
print("CHART: Trend chart saved.")
""",
            # ── 4. Cohort / Segment Analysis ─────────────────────────────
            "cohort_analysis": f"""\
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

{loader}

categ_cols   = [c for c in df.columns if df[c].dtype == object or df[c].nunique() < 15]
numeric_cols = df.select_dtypes(include='number').columns.tolist()

group_col  = "{x_col}" if "{x_col}" in df.columns else (categ_cols[0] if categ_cols else df.columns[0])
value_col  = "{y_col or (numeric_cols[0] if numeric_cols else 'value')}"
if value_col not in df.columns:
    value_col = numeric_cols[0] if numeric_cols else df.columns[1]

print(f"Segment analysis: {{value_col}} grouped by {{group_col}}")

grouped = df.groupby(group_col)[value_col].agg(['mean','sum','count']).round(2)
grouped.columns = ['Mean', 'Total', 'Count']
grouped = grouped.sort_values('Total', ascending=False).head(15)

print(grouped.to_string())
print()

palette = sns.color_palette("husl", len(grouped))
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle(f"Cohort Analysis: {{value_col}} by {{group_col}}", fontsize=13, fontweight="bold")

grouped['Total'].plot(kind='bar', ax=axes[0], color=palette, edgecolor='white')
axes[0].set_title("Total by Segment")
axes[0].set_xlabel(group_col)
axes[0].set_ylabel(f"Total {{value_col}}")
axes[0].tick_params(axis='x', rotation=30)

grouped['Mean'].plot(kind='bar', ax=axes[1], color=palette, edgecolor='white', alpha=0.85)
axes[1].set_title("Mean by Segment")
axes[1].set_xlabel(group_col)
axes[1].set_ylabel(f"Mean {{value_col}}")
axes[1].tick_params(axis='x', rotation=30)

plt.tight_layout()
{chart_save}
print("CHART: Cohort analysis chart saved.")
print(f"Top segment: {{grouped['Total'].idxmax()}} with total = {{grouped['Total'].max():.2f}}")
""",
            # ── 5. Bar Chart ─────────────────────────────────────────────
            "bar_chart": f"""\
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

{loader}

x_col = "{x_col}"
y_col = "{y_col}"
if x_col not in df.columns: x_col = df.columns[0]
numeric_cols = df.select_dtypes(include='number').columns.tolist()
if not y_col or y_col not in df.columns:
    y_col = numeric_cols[0] if numeric_cols else None

if y_col:
    data = df.groupby(x_col)[y_col].mean().sort_values(ascending=False).head(20)
    ylabel = f"Mean {{y_col}}"
else:
    data = df[x_col].value_counts().head(20)
    ylabel = "Count"

colors = sns.color_palette("husl", len(data))
fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.bar(range(len(data)), data.values, color=colors, edgecolor='white', linewidth=0.5)
ax.set_xticks(range(len(data)))
ax.set_xticklabels(data.index, rotation=35, ha='right')
ax.set_xlabel(x_col, fontsize=11)
ax.set_ylabel(ylabel, fontsize=11)
ax.set_title(f"{{ylabel}} by {{x_col}}", fontsize=13, fontweight="bold")
ax.spines[['top','right']].set_visible(False)
for bar in bars:
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, h * 1.01, f'{{h:.1f}}',
            ha='center', va='bottom', fontsize=7)
plt.tight_layout()
{chart_save}
print(f"CHART: Bar chart saved.")
print(f"Top category: {{data.idxmax()}} = {{data.max():.2f}}")
""",
            # ── 6. Pie Chart ─────────────────────────────────────────────
            "pie_chart": f"""\
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

{loader}

x_col = "{x_col}"
if x_col not in df.columns: x_col = df.columns[0]
counts = df[x_col].value_counts().head(10)
explode = [0.05] * len(counts)
colors  = plt.cm.Set3.colors[:len(counts)]
fig, ax = plt.subplots(figsize=(9, 7))
wedges, texts, autotexts = ax.pie(
    counts, labels=counts.index, autopct='%1.1f%%',
    explode=explode, colors=colors, startangle=140,
    pctdistance=0.8, wedgeprops=dict(linewidth=0.8, edgecolor='white')
)
for at in autotexts:
    at.set_fontsize(9)
ax.set_title(f"Distribution of {{x_col}}", fontsize=13, fontweight="bold")
plt.tight_layout()
{chart_save}
print(f"CHART: Pie chart saved. Largest segment: {{counts.idxmax()}} ({{counts.max() / counts.sum() * 100:.1f}}%)")
""",
            # ── 7. Scatter Plot ──────────────────────────────────────────
            "scatter_plot": f"""\
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

{loader}

numeric_cols = df.select_dtypes(include='number').columns.tolist()
x_col = "{x_col}" if "{x_col}" in df.columns and pd.api.types.is_numeric_dtype(df["{x_col}"]) else (numeric_cols[0] if numeric_cols else df.columns[0])
y_col = "{y_col}" if "{y_col}" in df.columns and pd.api.types.is_numeric_dtype(df["{y_col}"]) else (numeric_cols[1] if len(numeric_cols) > 1 else numeric_cols[0])

sample = df[[x_col, y_col]].dropna().sample(min(500, len(df)), random_state=42)
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(sample[x_col], sample[y_col], alpha=0.5, color="#6366f1", edgecolors="white", linewidths=0.3, s=40)
m, b = np.polyfit(sample[x_col], sample[y_col], 1)
x_line = np.linspace(sample[x_col].min(), sample[x_col].max(), 100)
ax.plot(x_line, m * x_line + b, color="#f59e0b", linewidth=2, label=f"Trend (y = {{m:.2f}}x + {{b:.2f}})")
ax.set_xlabel(x_col); ax.set_ylabel(y_col)
ax.set_title(f"{{x_col}} vs {{y_col}}", fontsize=13, fontweight="bold")
ax.legend(); ax.spines[['top','right']].set_visible(False)
plt.tight_layout()
{chart_save}
corr = sample[x_col].corr(sample[y_col])
print(f"CHART: Scatter plot saved.")
print(f"Pearson correlation: {{corr:.3f}}")
""",
            # ── 8. Histogram / Distribution ──────────────────────────────
            "histogram": f"""\
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

{loader}

numeric_cols = df.select_dtypes(include='number').columns.tolist()
target = "{y_col or x_col}"
if target not in df.columns or not pd.api.types.is_numeric_dtype(df.get(target)):
    target = numeric_cols[0] if numeric_cols else df.columns[0]

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle(f"Distribution Analysis: {{target}}", fontsize=13, fontweight="bold")
data = df[target].dropna()

axes[0].hist(data, bins=30, color="#6366f1", edgecolor="white", alpha=0.85)
axes[0].axvline(data.mean(),   color="#f59e0b", lw=2, linestyle='--', label=f"Mean: {{data.mean():.2f}}")
axes[0].axvline(data.median(), color="#10b981", lw=2, linestyle=':',  label=f"Median: {{data.median():.2f}}")
axes[0].legend(); axes[0].set_xlabel(target); axes[0].set_title("Histogram")

sns.boxplot(y=data, ax=axes[1], color="#a855f7", flierprops=dict(marker='o', markerfacecolor='#ef4444', markersize=4))
axes[1].set_title("Box Plot"); axes[1].set_ylabel(target)

plt.tight_layout()
{chart_save}
print(f"CHART: Distribution chart saved.")
print(f"Mean: {{data.mean():.3f}}, Std: {{data.std():.3f}}, Skew: {{data.skew():.3f}}")
""",
            # ── 9. Correlation Heatmap ───────────────────────────────────
            "correlation_heatmap": f"""\
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

{loader}

numeric_cols = df.select_dtypes(include='number').columns.tolist()
if len(numeric_cols) < 2:
    print("Not enough numeric columns for correlation analysis.")
else:
    corr = df[numeric_cols].corr()
    mask = np.triu(np.ones_like(corr, dtype=bool))
    fig, ax = plt.subplots(figsize=(max(8, len(numeric_cols)), max(6, len(numeric_cols) - 1)))
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="coolwarm",
                ax=ax, linewidths=0.5, linecolor='white',
                cbar_kws={{"shrink": 0.75, "label": "Pearson r"}})
    ax.set_title("Feature Correlation Heatmap", fontsize=13, fontweight="bold", pad=15)
    plt.tight_layout()
    {chart_save}
    print("CHART: Heatmap saved.")
    top = corr.abs().unstack().sort_values(ascending=False)
    top = [(i, j, v) for (i, j), v in top.items() if i != j and i < j]
    if top:
        i, j, v = top[0]
        print(f"Strongest correlation: {{i}} ↔ {{j}} = {{v:.3f}}")
""",
            # ── 10. Row Retrieval (fallback) ──────────────────────────────
            "row_retrieval": f"""\
import pandas as pd
import numpy as np

{loader}

df.columns = df.columns.str.strip()

# Try to find rank/id/name columns
rank_cols = [c for c in df.columns if any(k in c.lower() for k in ['rank', 'score', 'id', 'index', 'roll'])]
name_cols = [c for c in df.columns if any(k in c.lower() for k in ['name', 'candidate', 'student', 'person', 'user'])]

# Extract rank number from query
import re
numbers = [int(n) for n in re.findall(r'\\d+', "{user_message}")]
target_rank = numbers[0] if numbers else 70

found = False
if rank_cols:
    for col in rank_cols:
        # Check for numeric match
        try:
            df[col] = pd.to_numeric(df[col], errors='ignore')
            match = df[df[col] == target_rank]
            if not match.empty:
                name_val = match[name_cols[0]].values[0] if name_cols else match.iloc[0].to_dict()
                print(f"The {{target_rank}}th rank candidate is: {{name_val}}")
                found = True
                break
        except Exception:
            pass

if not found:
    # Fallback to row index (0-indexed or 1-indexed)
    idx = target_rank - 1
    if 0 <= idx < len(df):
        name_val = df.iloc[idx][name_cols[0]] if name_cols else df.iloc[idx].to_dict()
        print(f"The {{target_rank}}th candidate (at row index {{target_rank}}) is: {{name_val}}")
    else:
        print(f"The dataset does not contain a {{target_rank}}th record (total rows: {{len(df)}}).")
""",
            # ── 11. Auto-plot (fallback) ──────────────────────────────────
            "auto_plot": f"""\
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

{loader}

categ_cols   = [c for c in df.columns if df[c].dtype == object]
numeric_cols = df.select_dtypes(include='number').columns.tolist()

x_col = "{x_col}" if "{x_col}" in df.columns else (categ_cols[0] if categ_cols else df.columns[0])
y_col = "{y_col}" if "{y_col}" and "{y_col}" in df.columns else (numeric_cols[0] if numeric_cols else None)

if y_col:
    data = df.groupby(x_col)[y_col].mean().sort_values(ascending=False).head(15)
    ylabel = f"Mean {{y_col}}"
else:
    data = df[x_col].value_counts().head(15)
    ylabel = "Count"

colors = sns.color_palette("husl", len(data))
fig, ax = plt.subplots(figsize=(11, 5))
ax.bar(range(len(data)), data.values, color=colors, edgecolor='white')
ax.set_xticks(range(len(data)))
ax.set_xticklabels(data.index, rotation=35, ha='right')
ax.set_xlabel(x_col); ax.set_ylabel(ylabel)
ax.set_title(f"{{ylabel}} by {{x_col}}", fontsize=13, fontweight="bold")
ax.spines[['top','right']].set_visible(False)
plt.tight_layout()
{chart_save}
print(f"CHART: Chart saved.")
print(f"Category '{x_col}' has {{df[x_col].nunique()}} unique values.")
""",
        }

        code = templates.get(intent, templates["descriptive_summary"])
        return textwrap.dedent(code)
