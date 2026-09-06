"""
TypeScript analyzer implementation for code review.
"""

from analyzers.base_analyzer import BaseAnalyzer


class TypeScriptAnalyzer(BaseAnalyzer):
    def analyze(self, file_path: str) -> list[dict]:
        """
        Analyze TypeScript code using ESLint (simulated).
        """
        findings = []
        # In a real implementation, we would call eslint or use tree-sitter
        return findings

    def get_supported_extensions(self) -> list[str]:
        return [".ts", ".tsx"]
