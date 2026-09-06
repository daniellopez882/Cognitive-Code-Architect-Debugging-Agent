"""
Markdown reporter for code review summaries.

Proposed fixes, when the run asked for them, are rendered in their own section
and marked as not applied. The previous reporter ignored them entirely, so the
"fixes" the old node generated (a placeholder function) never reached anyone.
"""

from __future__ import annotations


class MarkdownReporter:
    def generate(self, findings: list[dict], proposed_fixes: list[dict] | None = None) -> str:
        report = "# Code Review Report\n\n"
        if not findings:
            report += "No issues found.\n"
        for finding in findings:
            report += f"## {finding.get('title', 'Issue')}\n"
            report += f"- **Severity**: {finding.get('severity', 'Info')}\n"
            report += f"- **File**: {finding.get('file', 'N/A')}\n"
            report += f"- **Description**: {finding.get('description', '')}\n\n"

        if proposed_fixes:
            report += "## Proposed fixes (not applied)\n\n"
            report += (
                "Model proposals for a reviewer to consider. Nothing was written to the "
                "repository; check each one before using it.\n\n"
            )
            for fix in proposed_fixes:
                where = f"{fix.get('file') or 'N/A'}:{fix.get('line') or '?'}"
                report += f"### {fix.get('title') or fix.get('issue_id')} ({where})\n"
                if fix.get("status") == "proposed":
                    report += f"```python\n{fix['proposed_code']}\n```\n\n"
                else:
                    report += f"_No usable proposal ({fix.get('status')})._\n\n"

        return report
