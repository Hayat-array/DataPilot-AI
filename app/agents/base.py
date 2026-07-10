import logging
import os

class BaseAgent:
    """Base Agent providing standard logging, state tracking, and integration placeholders."""
    def __init__(self, name, role=""):
        self.name = name
        self.role = role
        self.logger = logging.getLogger("agent")
        self.logger.info(f"Initialized agent: {self.name} with role: {self.role}")

    def log_step(self, step_name, details=None):
        """Logs an agent action to the specialized agent log file."""
        log_msg = f"[{self.name}] Step: {step_name}"
        if details:
            log_msg += f" | Details: {details}"
        self.logger.info(log_msg)

    def execute(self, *args, **kwargs):
        """Standard entry point for executing agent workflow."""
        raise NotImplementedError("Subclasses must implement execute method.")
