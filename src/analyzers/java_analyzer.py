"""
Java analyzer implementation for code review.
"""

from analyzers.base_analyzer import BaseAnalyzer


class JavaAnalyzer(BaseAnalyzer):
    def analyze(self, file_path: str) -> list[dict]:
        """
        Analyze Java code using PMD or Checkstyle (simulated).
        """
        findings = []
        # In a real implementation, we would call a Java linter or use tree-sitter
        return findings

    def get_supported_extensions(self) -> list[str]:
        return [".java"]
