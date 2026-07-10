from app.agents.base import BaseAgent

class MemoryManager(BaseAgent):
    """Memory Manager preserves state parameters and conversation buffers to retain workspace context."""
    def __init__(self):
        super().__init__("MemoryManager", "Manages session variables and context history.")
        self.variables_cache = {}

    def execute(self, action="get", key=None, val=None):
        self.log_step("manage_memory", f"Performing action '{action}' on key '{key}'")
        
        if action == "set" and key:
            self.variables_cache[key] = val
            return True
        elif action == "get" and key:
            return self.variables_cache.get(key)
        elif action == "clear":
            self.variables_cache.clear()
            return True
        return self.variables_cache
