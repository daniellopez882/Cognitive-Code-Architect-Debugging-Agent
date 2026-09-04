"""
Base class for code analyzers.
"""

from abc import ABC, abstractmethod


class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self, file_path: str) -> list[dict]:
        pass

    @abstractmethod
    def get_supported_extensions(self) -> list[str]:
        pass
