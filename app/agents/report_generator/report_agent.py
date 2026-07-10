from app.agents.base import BaseAgent

class ReportAgent(BaseAgent):
    """Report Agent compiles findings, insights, metrics and charts into professional PDF/Markdown reports."""
    def __init__(self):
        super().__init__("ReportGenerator", "Assembles executive summary reports.")

    def execute(self, findings, charts_list):
        self.log_step("generate_report", "Creating analytical markdown report.")
        
        report_md = f"""# DataPilot AI - Analysis Executive Summary

## Findings
{findings}

## Visualizations
"""
        for chart in charts_list:
            report_md += f"- ![{chart}]({chart})\n"
            
        self.log_step("report_compiled", "Report compilation complete.")
        return report_md
