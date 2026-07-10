import os
import subprocess
import sys
import uuid
from app.agents.base import BaseAgent

class ExecutorAgent(BaseAgent):
    """Executor Agent executes generated Python scripts inside an isolated/designated directory context."""
    def __init__(self):
        super().__init__("Executor", "Executes Python code scripts safely.")

    def execute(self, code_string, sandbox_dir="generated_code/sandbox"):
        self.log_step("execution_started", "Executing code snippet")
        
        # Ensure directories exist
        os.makedirs(sandbox_dir, exist_ok=True)
        
        # Save code to file
        file_name = f"script_{uuid.uuid4().hex[:8]}.py"
        file_path = os.path.join(sandbox_dir, file_name)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code_string)
            
        self.log_step("script_saved", f"Saved script to {file_path}")
        
        # Run python script in subprocess
        try:
            result = subprocess.run(
                [sys.executable, file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.log_step("execution_success", f"Script completed: {result.stdout.strip()}")
                return {
                    "success": True,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "file_path": file_path
                }
            else:
                self.log_step("execution_failed", f"Exit code {result.returncode} | Stderr: {result.stderr.strip()}")
                return {
                    "success": False,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "file_path": file_path
                }
        except subprocess.TimeoutExpired:
            self.log_step("execution_timeout", "Script execution timed out after 30 seconds.")
            return {
                "success": False,
                "stdout": "",
                "stderr": "Execution timed out.",
                "file_path": file_path
            }
        except Exception as e:
            self.log_step("execution_error", f"System error executing script: {str(e)}")
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "file_path": file_path
            }
