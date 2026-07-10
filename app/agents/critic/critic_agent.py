"""
CriticAgent — Analyzes failed code, queries RAG knowledge base for fixes,
and produces corrected Python code. Core of the self-correction loop.
"""

import os
import re
import textwrap
from app.agents.base import BaseAgent


# ── Built-in Pandas/NumPy fix recipes (the lightweight RAG corpus) ─────────
FIX_RECIPES = {
    "KeyError": """\
# FIX: KeyError — column name mismatch
# Strip whitespace from column names
df.columns = df.columns.str.strip()
# Use df.columns.tolist() to inspect actual names
""",
    "ModuleNotFoundError": """\
# FIX: Only use standard libraries: pandas, numpy, matplotlib, seaborn
# Replace any unavailable library with its standard equivalent
""",
    "ValueError: could not convert string to float": """\
# FIX: Coerce strings to numeric before arithmetic
df[col] = pd.to_numeric(df[col], errors='coerce')
df = df.dropna(subset=[col])
""",
    "FileNotFoundError": """\
# FIX: Verify dataset path is quoted correctly
# Use raw string: r"path\\to\\file.csv"
""",
    "SettingWithCopyWarning": """\
# FIX: Avoid chained assignment; use .loc
df.loc[condition, col] = value
""",
    "AttributeError: 'DataFrame' object has no attribute 'append'": """\
# FIX: DataFrame.append() was removed in Pandas 2.0
# Use pd.concat([df1, df2], ignore_index=True) instead
""",
    "TypeError: '<' not supported between instances of 'str' and 'float'": """\
# FIX: Mixed types in column; convert to numeric or string uniformly
df[col] = pd.to_numeric(df[col], errors='coerce')
""",
    "MemoryError": """\
# FIX: Dataset too large; read in chunks or sample
df = pd.read_csv(path, nrows=5000)  # sample first N rows
""",
    "plt.show": """\
# FIX: Use plt.savefig(output_path) instead of plt.show() in server context
# Replace: plt.show()  →  plt.savefig(output_path, dpi=150, bbox_inches='tight'); plt.close()
""",
    "default": """\
# FIX: General corrections applied
# - Strip column names: df.columns = df.columns.str.strip()
# - Convert types safely: pd.to_numeric(df[col], errors='coerce')
# - Use matplotlib Agg backend: matplotlib.use('Agg') before importing pyplot
# - Save charts: plt.savefig(path); plt.close() — do NOT call plt.show()
""",
}

GROQ_CORRECTION_PROMPT = """\
You are a Python debugging expert. The following code raised an error.
Fix ONLY the bug — keep the logic intact. Return ONLY the corrected Python code,
no explanation. Start directly with `import`.

Error:
{error}

Documentation hints:
{hint}

Original code:
{code}
"""


class CriticAgent(BaseAgent):
    """Critiques failed code and produces corrected version using RAG hints and LLM."""

    def __init__(self):
        super().__init__("Critic", "Self-corrects failed Python code using RAG and LLM.")
        self._groq_client = None
        self._init_groq()

    def _init_groq(self):
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            return
        try:
            from groq import Groq
            self._groq_client = Groq(api_key=api_key)
        except Exception:
            pass

    # ── RAG retrieval (keyword-matched local corpus) ───────────────────────
    def _retrieve_hint(self, error_message: str) -> str:
        for keyword, recipe in FIX_RECIPES.items():
            if keyword.lower() in error_message.lower():
                return recipe
        return FIX_RECIPES["default"]

    # ── Rule-based code patch (no LLM needed) ─────────────────────────────
    def _apply_rule_patch(self, code: str, error_message: str) -> str:
        patched = code

        # Always ensure Agg backend for headless server
        if "matplotlib.use('Agg')" not in patched:
            patched = "import matplotlib\nmatplotlib.use('Agg')\n" + patched

        # Fix plt.show()
        patched = re.sub(r"\bplt\.show\(\)", "# plt.show() disabled on server", patched)

        if "KeyError" in error_message:
            patched = re.sub(
                r"(df\s*=\s*pd\.read_[^\n]+\n)",
                r"\1df.columns = df.columns.str.strip()\n",
                patched,
                count=1
            )
        if "could not convert string to float" in error_message or "TypeError" in error_message:
            # Add numeric coercion after dataframe load
            patched = re.sub(
                r"(df\s*=\s*pd\.read_[^\n]+\n)",
                r"\1# Auto-coerce numeric columns\n"
                r"for _c in df.columns:\n"
                r"    try: df[_c] = pd.to_numeric(df[_c], errors='ignore')\n"
                r"    except: pass\n",
                patched,
                count=1
            )

        return patched

    # ── LLM correction ─────────────────────────────────────────────────────
    def _correct_via_groq(self, code: str, error_message: str, hint: str) -> str:
        if not self._groq_client:
            return ""
        try:
            prompt = GROQ_CORRECTION_PROMPT.format(
                error=error_message[:800],
                hint=hint[:600],
                code=code[:2000],
            )
            resp = self._groq_client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1600,
            )
            raw = resp.choices[0].message.content.strip()
            code_out = re.sub(r"^```python\n?", "", raw)
            code_out = re.sub(r"\n?```$", "", code_out)
            return code_out.strip()
        except Exception as e:
            self.log_step("groq_critic_error", str(e))
            return ""

    # ── Public API ─────────────────────────────────────────────────────────
    def execute(self, code: str, error_message: str, attempt: int = 1) -> dict:
        """
        Produce corrected code given the original code and the error.

        Returns:
            {corrected_code, suggestion, hint_used, method}
        """
        self.log_step("critic_start",
                      f"Attempt #{attempt} — Analyzing: {error_message[:80]}")

        hint = self._retrieve_hint(error_message)
        self.log_step("rag_retrieved", f"RAG hint retrieved ({len(hint)} chars)")

        # Try LLM first
        corrected = self._correct_via_groq(code, error_message, hint)
        method = "llm"

        if not corrected:
            # Fall back to rule-based patch
            corrected = self._apply_rule_patch(code, error_message)
            method = "rule_patch"

        self.log_step("correction_ready",
                      f"Corrected code produced via {method} ({len(corrected)} chars)")

        return {
            "corrected_code": corrected,
            "suggestion":     hint.strip()[:200],
            "hint_used":      hint,
            "method":         method,
            "can_retry":      True,
        }
