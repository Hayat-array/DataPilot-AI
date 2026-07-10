from app.agents.base import BaseAgent

class InsightAgent(BaseAgent):
    """Insight Generator Agent scans distributions, correlations and variables to report findings."""
    def __init__(self):
        super().__init__("InsightGenerator", "Derives mathematical and structural patterns.")

    def execute(self, df_describe_dict):
        self.log_step("generate_insights", "Reviewing dataset descriptive stats.")
        
        insights = []
        for col, stats in df_describe_dict.items():
            if "mean" in stats:
                insights.append(f"Column '{col}' has a mean value of {stats['mean']:.2f}")
            if "nulls" in stats and stats["nulls"] > 0:
                insights.append(f"Column '{col}' contains {stats['nulls']} missing values.")
                
        self.log_step("insights_derived", f"Derived {len(insights)} analytical insights.")
        return insights
