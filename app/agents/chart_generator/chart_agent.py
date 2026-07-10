from app.agents.base import BaseAgent

class ChartAgent(BaseAgent):
    """Chart Generator Agent creates configurations or python code to build visualization elements."""
    def __init__(self):
        super().__init__("ChartGenerator", "Generates Plotly and Matplotlib charts.")

    def execute(self, df_metadata, chart_type="bar"):
        self.log_step("generate_chart", f"Generating code for chart type: {chart_type}")
        
        # Simple plot generation python block builder
        chart_code = f"""# Plot generation block
import matplotlib.pyplot as plt
import seaborn as sns

plt.figure(figsize=(10, 6))
# Render basic plot skeleton
plt.title("Data Pilot Auto Generated plot")
plt.savefig("outputs/plots/auto_plot.png")
plt.close()
"""
        self.log_step("chart_code_generated", "Chart code compiled successfully.")
        return chart_code
