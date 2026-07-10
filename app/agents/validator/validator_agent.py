import os
from app.agents.base import BaseAgent

class ValidatorAgent(BaseAgent):
    """Validator Agent validates file formats, dataset structure, and executions outputs."""
    def __init__(self):
        super().__init__("Validator", "Validates input integrity and output conformity.")

    def execute(self, file_path):
        self.log_step("validate_file", f"Inspecting integrity of file: {file_path}")
        
        if not os.path.exists(file_path):
            self.log_step("validation_error", "File does not exist on filesystem.")
            return {"valid": False, "reason": "File not found."}
            
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            self.log_step("validation_error", "Uploaded file is empty (0 bytes).")
            return {"valid": False, "reason": "File is empty."}
            
        ext = os.path.splitext(file_path)[1].lower()
        allowed = [".csv", ".xlsx", ".xls", ".json"]
        
        if ext not in allowed:
            self.log_step("validation_error", f"Extension '{ext}' is not supported.")
            return {"valid": False, "reason": f"Extension '{ext}' not supported. Allowed: {allowed}"}
            
        self.log_step("validation_success", f"File size: {file_size} bytes | Format: {ext}")
        return {"valid": True, "size": file_size, "format": ext}
