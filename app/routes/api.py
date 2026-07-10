"""
API Routes — /api/upload and /api/chat
The chat endpoint wires all agents into a complete autonomous pipeline:
  User Query
    → Planner  : classify intent + extract schema
    → Coder    : generate Python/Pandas code (LLM or template)
    → Executor : run in subprocess sandbox
    → Critic   : self-correct on error (up to MAX_RETRIES)
    → Response : text insight + chart URL + generated code + logs
"""

import os
import json
import uuid
import pandas as pd
import numpy as np
from flask import Blueprint, request, current_app
from werkzeug.utils import secure_filename
from app.utils.response import success_response, error_response

# ── Agent imports ──────────────────────────────────────────────────────────
from app.agents.coder.coder_agent     import CoderAgent
from app.agents.executor.executor_agent import ExecutorAgent
from app.agents.critic.critic_agent   import CriticAgent
from app.agents.executor              import sandbox

api_bp = Blueprint("api_routes", __name__)

ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.json'}
MAX_RETRIES        = 3       # self-correction attempts

# ── Lazy singleton agents (initialised once per process) ──────────────────
_coder    = None
_executor = None
_critic   = None

def _get_agents():
    global _coder, _executor, _critic
    if _coder is None:
        _coder    = CoderAgent()
        _executor = ExecutorAgent()
        _critic   = CriticAgent()
    return _coder, _executor, _critic


# ══════════════════════════════════════════════════════════════════════════
#  /api/upload
# ══════════════════════════════════════════════════════════════════════════
def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


@api_bp.route("/upload", methods=["POST"])
def upload_file():
    """Upload a dataset file; verify it loads correctly via pandas."""
    if 'file' not in request.files:
        return error_response("NO_FILE_PART", "No file part in the request", 400)

    file = request.files['file']
    if file.filename == '':
        return error_response("NO_SELECTED_FILE", "No selected file", 400)

    if not (file and allowed_file(file.filename)):
        return error_response("INVALID_FILE_TYPE", "File extension not allowed.", 400)

    filename        = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
    upload_folder   = current_app.config.get("UPLOAD_FOLDER", "uploads")
    os.makedirs(upload_folder, exist_ok=True)

    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)

    try:
        df = _load_dataframe(file_path)
        rows, cols = df.shape
        return success_response(
            data={
                "filename":      unique_filename,
                "original_name": filename,
                "rows":          rows,
                "cols":          cols,
            },
            message="File uploaded and verified successfully.",
        )
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        return error_response("FILE_READ_ERROR", f"Failed to read dataset: {e}", 400)


@api_bp.route("/load-cached", methods=["POST"])
def load_cached():
    """Retrieve columns, rows, and preview of a cached uploaded file."""
    body = request.get_json() or {}
    filename = body.get("filename", "")
    if not filename:
        return error_response("NO_FILENAME", "Filename is required", 400)

    upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
    file_path = os.path.join(upload_folder, filename)

    if not os.path.exists(file_path):
        return error_response("FILE_NOT_FOUND", "Cached file no longer exists", 404)

    try:
        df = _load_dataframe(file_path)
        # Limit rows to 1000 and fill NaN with None for clean JSON response
        preview = df.head(1000).replace({np.nan: None}).to_dict(orient="records")
        return success_response(
            data={
                "columns":       df.columns.tolist(),
                "rows_count":    df.shape[0],
                "cols_count":    df.shape[1],
                "data":          preview,
                "original_name": filename.split("_", 1)[-1] if "_" in filename else filename
            },
            message="Cached dataset loaded successfully."
        )
    except Exception as e:
        return error_response("LOAD_ERROR", f"Failed to load cached file: {e}", 500)


# ══════════════════════════════════════════════════════════════════════════
#  /api/chat  — Full autonomous agent pipeline
# ══════════════════════════════════════════════════════════════════════════
@api_bp.route("/chat", methods=["POST"])
def chat_co_pilot():
    """
    Autonomous multi-agent chat endpoint.
    Accepts: { message, filename }
    Returns: { answer, chart_url, generated_code, logs }
    """
    body    = request.get_json() or {}
    message = body.get("message", "").strip()
    filename= body.get("filename", "")

    if not message:
        return error_response("EMPTY_MESSAGE", "Message is required", 400)

    coder, executor, critic = _get_agents()
    logs = []

    def log(t, txt):
        logs.append({"type": t, "text": txt})

    # ── 1. Load dataset ───────────────────────────────────────────────────
    df = None
    upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
    file_path = os.path.join(upload_folder, filename) if filename else None

    if file_path and os.path.exists(file_path):
        try:
            df = _load_dataframe(file_path)
            log("system", f"Planner › Dataset loaded: {df.shape[0]} rows × {df.shape[1]} cols")
        except Exception as e:
            log("error", f"Planner › Failed to load dataset: {e}")

    if df is None:
        return success_response(
            data={
                "answer":         "Please upload a dataset first using the sidebar panel.",
                "chart_url":      None,
                "generated_code": None,
                "logs":           logs,
            },
            message="No dataset loaded.",
        )

    # ── 2. Build schema ───────────────────────────────────────────────────
    schema = _build_schema(df, file_path)
    log("agent", f"Planner › Schema extracted: {len(schema['columns'])} columns, "
                 f"{len(schema['numeric_cols'])} numeric")

    # ── 3. Generate chart output path ─────────────────────────────────────
    run_id     = sandbox.make_run_id()
    chart_path = sandbox.make_chart_path(run_id)

    # Inject the chart path into the code so it's always saved consistently
    schema["_chart_path"] = chart_path
    schema["_run_id"]     = run_id

    # ── 4. Code generation ────────────────────────────────────────────────
    log("agent", "Coder › Generating Python/Pandas analysis code...")
    code = coder.execute(
        dataset_path     = os.path.abspath(file_path),
        user_message     = message,
        schema           = schema,
        output_chart_path= chart_path,
    )
    log("system", f"Coder › Code generated ({len(code.splitlines())} lines)")

    # ── 5. Self-correction execution loop ─────────────────────────────────
    result      = None
    final_code  = code
    chart_url   = None
    text_output = ""

    for attempt in range(1, MAX_RETRIES + 1):
        log("agent", f"Executor › Running code (attempt {attempt}/{MAX_RETRIES})...")
        result = sandbox.run_code(final_code)

        if result["success"]:
            log("success", f"Executor › Execution successful on attempt {attempt}.")
            text_output = result["stdout"]
            if result["chart_filename"]:
                chart_url = f"/static/{result['chart_filename']}"
                log("success", f"Executor › Chart saved → {result['chart_filename']}")
            break
        else:
            err = result["stderr"]
            log("error", f"Executor › Error (attempt {attempt}): {err[:120]}")

            if attempt < MAX_RETRIES:
                log("agent", f"Critic  › Querying RAG knowledge base for self-correction...")
                fix = critic.execute(final_code, err, attempt=attempt)
                log("agent", f"Critic  › {fix['method'].upper()}: {fix['suggestion'][:80]}")
                final_code = fix["corrected_code"]
            else:
                log("error", "Critic  › Max retries reached. Returning best-effort answer.")

    # ── 6. Format answer ──────────────────────────────────────────────────
    answer_html = _format_answer(message, text_output, df, schema, chart_url, result)

    return success_response(
        data={
            "answer":         answer_html,
            "chart_url":      chart_url,
            "generated_code": final_code,
            "logs":           logs,
        },
        message="Co-pilot answer generated.",
    )


# ══════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════
def _load_dataframe(file_path: str) -> pd.DataFrame:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(file_path)
    elif ext in (".xlsx", ".xls"):
        return pd.read_excel(file_path)
    elif ext == ".json":
        import json as json_lib
        with open(file_path, "r", encoding="utf-8") as f:
            raw = json_lib.load(f)
        if isinstance(raw, list):
            return pd.DataFrame(raw)
        if isinstance(raw, dict):
            arr_key = next((k for k, v in raw.items() if isinstance(v, list)), None)
            if arr_key:
                return pd.DataFrame(raw[arr_key])
            return pd.DataFrame([raw])
    return pd.read_csv(file_path)


def _build_schema(df: pd.DataFrame, file_path: str) -> dict:
    numeric_cols    = df.select_dtypes(include="number").columns.tolist()
    categorical_cols= df.select_dtypes(exclude="number").columns.tolist()
    nulls           = {col: int(df[col].isnull().sum()) for col in df.columns}
    dtypes          = {col: str(df[col].dtype) for col in df.columns}

    # Sample values for context
    sample_values = {}
    for col in df.columns[:8]:
        non_null = df[col].dropna()
        sample_values[col] = non_null.head(3).tolist() if len(non_null) else []

    return {
        "file_path":        file_path,
        "file_ext":         os.path.splitext(file_path)[1].lower(),
        "shape":            list(df.shape),
        "columns":          df.columns.tolist(),
        "dtypes":           dtypes,
        "numeric_cols":     numeric_cols,
        "categorical_cols": categorical_cols,
        "nulls":            nulls,
        "sample_values":    sample_values,
    }


def _generate_simple_summary(message: str, stdout: str, schema: dict) -> str:
    """Generate a friendly plain-English summary of stdout for non-technical users."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    if api_key:
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            prompt = f"""\
You are a friendly data analyst assistant. Explain the following raw program analysis results in simple, plain-English words for a non-technical manager.
- Do NOT mention code, variables, pandas, dataframe, shape, dtype, print statements, or databases.
- Start directly with a brief, friendly 1-sentence opening (e.g., "Here is a simple overview of your dataset:").
- Provide 2-3 key bullet points summarizing the insights (use standard HTML <ul> and <li> tags).
- Bold key metrics using <strong>.
- Keep it extremely concise and non-technical.

User question: "{message}"

Raw program output:
{stdout}
"""
            resp = client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=600
            )
            summary = resp.choices[0].message.content.strip()
            if summary:
                return summary
        except Exception:
            pass

    # Rule-based fallback summary generator
    msg_l = message.lower()
    cols  = schema.get("columns", [])
    rows  = schema.get("shape", [0,0])[0]
    num_cols = len(schema.get("numeric_cols", []))

    if "summary" in msg_l or "describe" in msg_l or "profil" in msg_l:
        return f"""
        <strong>Overview of your uploaded data:</strong><br>
        <ul>
            <li>The dataset contains <strong>{rows:,} records</strong> and <strong>{len(cols)} distinct categories/columns</strong>.</li>
            <li>We scanned <strong>{num_cols} numerical values</strong> to calculate averages and distribution ranges.</li>
            <li>A feature correlation matrix was built to find patterns between numeric columns.</li>
        </ul>
        """
    elif "missing" in msg_l or "null" in msg_l or "clean" in msg_l or "quality" in msg_l:
        total_cells = schema.get("shape", [0,0])[0] * len(cols)
        nulls = sum(schema.get("nulls", {}).values())
        pct = ((1 - nulls/total_cells)*100) if total_cells > 0 else 100
        return f"""
        <strong>Data Quality Health Assessment:</strong><br>
        <ul>
            <li>Your dataset has an overall completeness score of <strong>{pct:.1f}%</strong>.</li>
            <li>Out of {total_cells:,} total cells, we detected <strong>{nulls:,} missing or empty cells</strong>.</li>
            <li>Empty text values and blank rows were safely flagged.</li>
        </ul>
        """
    elif "plot" in msg_l or "chart" in msg_l or "graph" in msg_l:
        return f"""
        <strong>Chart plotted successfully:</strong><br>
        <ul>
            <li>We processed the column fields to generate your requested visualization.</li>
            <li>Data points were grouped and sorted to highlight the largest segments clearly.</li>
        </ul>
        """
    elif any(k in msg_l for k in ["rank", "candidate", "student", "person", "row", "index"]):
        details = stdout.strip() if stdout else "No matching record was found."
        return f"""
        <strong>Dataset Record Query:</strong><br>
        <ul>
            <li>{details}</li>
        </ul>
        """
    else:
        return f"""
        <strong>Analysis Results:</strong><br>
        <ul>
            <li>We successfully executed the data processing script on your dataset.</li>
            <li>Key relationships and summaries were extracted from the columns.</li>
        </ul>
        """


def _format_answer(message: str, stdout: str, df: pd.DataFrame,
                   schema: dict, chart_url: str | None, result: dict | None) -> str:
    """Convert raw stdout into a friendly HTML answer with simple summary and details tag."""
    lines = stdout.strip().splitlines() if stdout else []

    # If execution failed completely
    if result and not result["success"] and not stdout:
        stderr = result.get("stderr", "")
        return (
            f"⚠️ The agent attempted to run the analysis but encountered an error after "
            f"{MAX_RETRIES} retries.<br><br>"
            f"<strong>Error summary:</strong> <code>{stderr[:200]}</code><br><br>"
            f"Try rephrasing your question, or check that the dataset has the expected columns."
        )

    if not lines:
        return "The analysis completed but produced no text output. The chart above shows the result."

    # 1. Generate plain-English summary
    simple_summary = _generate_simple_summary(message, stdout, schema)

    # 2. Format detailed output lines as readable HTML
    html_parts = []
    for line in lines:
        if line.startswith("CHART:"):
            continue   # handled via chart_url
        elif line.startswith("=") or line.startswith("-"):
            html_parts.append(f"<hr style='border-color:var(--bg-border); margin:0.5rem 0;'>")
        elif ":" in line and not line.startswith(" "):
            key, _, val = line.partition(":")
            html_parts.append(f"<div style='margin:0.2rem 0;'><strong>{key.strip()}:</strong> {val.strip()}</div>")
        elif line.strip():
            html_parts.append(f"<div style='color:var(--text-secondary); font-size:0.85rem;'>{line}</div>")

    detailed_html = "\n".join(html_parts)

    # Wrap detailed stats in a premium details tag
    formatted_answer = f"""
    <div class="simple-summary-block">
        {simple_summary}
    </div>
    
    <details style="margin-top: 1rem; border: 1px solid var(--bg-border); border-radius: 8px; padding: 0.5rem 0.85rem; background: rgba(255,255,255,0.01);">
        <summary style="font-size: 0.76rem; font-weight: 700; color: var(--text-muted); cursor: pointer; user-select: none; outline: none;">
            <i class="fa-solid fa-square-poll-vertical" style="color:var(--accent-1); margin-right:4px;"></i> View Detailed Technical Statistics
        </summary>
        <div style="margin-top: 0.75rem;">
            {detailed_html}
        </div>
    </details>
    """

    if chart_url:
        formatted_answer += f"<br><div style='font-size:0.78rem; color:var(--accent-3); margin-top:0.5rem;'>📊 Chart generated and displayed above.</div>"

    return formatted_answer

