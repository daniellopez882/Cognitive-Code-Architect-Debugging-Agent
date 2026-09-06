"""
State definitions for the Code Review Agent.
"""

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage


class Finding(TypedDict):
    """Structure for a single finding."""

    id: str
    file: str
    line: int
    column: int | None
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    category: str  # 'bug', 'security', 'performance', 'style', etc.
    title: str
    description: str
    impact: str
    recommendation: str
    code_snippet: str | None
    suggested_fix: str | None
    auto_fixable: bool
    references: list[str]
    cwe_id: str | None  # For security issues
    cvss_score: float | None  # For security issues


class CodeReviewState(TypedDict):
    """
    Complete state for the code review agent.
    Uses Annotated with operator.add for list fields to accumulate values.
    """

    # Input parameters
    repository_url: str
    local_path: str
    review_scope: str
    target_branch: str | None
    target_files: list[str] | None

    # Repository metadata
    primary_languages: list[str]
    project_type: str
    frameworks: list[str]
    build_tools: list[str]

    # Configuration
    config: dict
    severity_threshold: str
    auto_fix_enabled: bool

    # Analysis results (accumulated across nodes)
    static_analysis_findings: Annotated[list[Finding], operator.add]
    pattern_analysis_findings: Annotated[list[Finding], operator.add]
    security_findings: Annotated[list[Finding], operator.add]
    performance_findings: Annotated[list[Finding], operator.add]
    testing_findings: Annotated[list[Finding], operator.add]
    logic_findings: Annotated[list[Finding], operator.add]
    policy_findings: Annotated[list[Finding], operator.add]

    # Synthesized results
    all_findings: list[Finding]
    prioritized_issues: list[Finding]
    quick_wins: list[Finding]

    # Fix generation
    generated_fixes: list[dict]
    fix_branch_name: str | None

    # Reporting
    markdown_report: str
    json_report: dict
    github_issues: list[dict]

    # Conversation
    messages: Annotated[list[BaseMessage], operator.add]
    current_step: str
    errors: Annotated[list[str], operator.add]

    # Progress tracking
    files_analyzed: int
    total_files: int
    analysis_start_time: float

    # User preferences
    user_feedback: list[dict]
    skip_categories: list[str]
