from app.agents.base import BaseAgent

class PlannerAgent(BaseAgent):
    """Planner Agent coordinates and plans the data analysis steps based on user input and profiling results."""
    def __init__(self):
        super().__init__("Planner", "Orchestrates multi-agent analysis plans.")

    def execute(self, user_query, dataset_metadata=None):
        self.log_step("create_plan", f"Creating plan for query: {user_query}")
        
        # Skeleton plan generation
        plan = {
            "query": user_query,
            "steps": [
                {"step_id": 1, "agent": "Validator", "description": "Validate uploaded file structure."},
                {"step_id": 2, "agent": "Cleaner", "description": "Clean missing values and format data types."},
                {"step_id": 3, "agent": "InsightGenerator", "description": "Identify distributions, outliers, and key statistical insights."},
                {"step_id": 4, "agent": "Coder", "description": "Generate processing and chart code."},
                {"step_id": 5, "agent": "Executor", "description": "Run Python script to output datasets and plots."},
                {"step_id": 6, "agent": "ReportGenerator", "description": "Compile HTML/PDF report."}
            ]
        }
        
        self.log_step("plan_created", f"Formulated {len(plan['steps'])} steps.")
        return plan
