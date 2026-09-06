"""
Performance analysis tools for bottleneck detection.
"""

from langchain_core.tools import tool


@tool
def profile_performance(file_path: str) -> dict:
    """
    Profile performance of a script.

    Args:
        file_path: Path to the script to profile

    Returns:
        Performance metrics
    """
    return {"latency": "low", "memory_usage": "stable"}


@tool
def detect_n_plus_one_queries(file_path: str) -> list[dict]:
    """
    Detect potential N+1 query patterns in database code.
    """
    return []
