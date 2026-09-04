"""
Markdown reporter for generating code review summaries.
"""


class MarkdownReporter:
    def generate(self, findings: list[dict]) -> str:
        report = "# Code Review Report\n\n"
        if not findings:
            report += "No issues found."
            return report

        for finding in findings:
            report += f"## {finding.get('title', 'Issue')}\n"
            report += f"- **Severity**: {finding.get('severity', 'Info')}\n"
            report += f"- **File**: {finding.get('file', 'N/A')}\n"
            report += f"- **Description**: {finding.get('description', '')}\n\n"

        return report
