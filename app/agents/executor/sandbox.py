"""
Sandbox — safe subprocess-based Python code execution.
Captures stdout (text insights) and detects saved chart files.
"""

import os
import sys
import uuid
import subprocess


SANDBOX_DIR  = os.path.join(os.path.dirname(__file__), "..", "..", "..", "generated_code", "sandbox")
CHARTS_DIR   = os.path.join(os.path.dirname(__file__), "..", "..", "..", "app", "static", "charts")
TIMEOUT_SECS = 45


def run_code(code_string: str) -> dict:
    """
    Execute Python code in an isolated subprocess.

    Returns:
        {
            success (bool),
            stdout  (str),
            stderr  (str),
            chart_filename (str | None),   # relative to static/charts/
            script_path (str)
        }
    """
    os.makedirs(SANDBOX_DIR, exist_ok=True)
    os.makedirs(CHARTS_DIR,  exist_ok=True)

    script_id   = uuid.uuid4().hex[:10]
    script_path = os.path.join(SANDBOX_DIR, f"script_{script_id}.py")

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(code_string)

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECS,
            cwd=os.path.dirname(script_path),
        )
        success = result.returncode == 0
        return {
            "success":        success,
            "stdout":         result.stdout.strip(),
            "stderr":         result.stderr.strip(),
            "chart_filename": _find_chart(script_id),
            "script_path":    script_path,
        }
    except subprocess.TimeoutExpired:
        return {
            "success":        False,
            "stdout":         "",
            "stderr":         f"Execution timed out after {TIMEOUT_SECS} seconds.",
            "chart_filename": None,
            "script_path":    script_path,
        }
    except Exception as e:
        return {
            "success":        False,
            "stdout":         "",
            "stderr":         str(e),
            "chart_filename": None,
            "script_path":    script_path,
        }


def make_chart_path(script_id: str) -> str:
    """Return the absolute chart output path for a given script run id."""
    os.makedirs(CHARTS_DIR, exist_ok=True)
    return os.path.join(CHARTS_DIR, f"chart_{script_id}.png")


def _find_chart(script_id: str) -> str | None:
    """Return the chart filename (relative to static/) if it was saved."""
    expected = os.path.join(CHARTS_DIR, f"chart_{script_id}.png")
    if os.path.isfile(expected):
        return f"charts/chart_{script_id}.png"
    return None


def make_run_id() -> str:
    return uuid.uuid4().hex[:10]
