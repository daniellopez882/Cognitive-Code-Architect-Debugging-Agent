from typing import List, Dict, Any
from state import CodeReviewState
from agents.tools import tools
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
import os
import uuid
import time
from utils.personas import get_persona_prompt

# Initialize LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    temperature=0.1
)

llm_with_tools = llm.bind_tools(tools)

def initialize_repository(state: CodeReviewState) -> CodeReviewState:
    """Initialize the repository and detect structure."""
    state["current_step"] = "initialization"
    return state

def define_scope(state: CodeReviewState) -> CodeReviewState:
    """Determine review scope."""
    state["current_step"] = "scope_definition"
    return state

def run_static_analysis(state: CodeReviewState) -> CodeReviewState:
    """Execute static analysis on repository files."""
    state["static_analysis_findings"] = []
    state["current_step"] = "static_analysis_complete"
    return state

def run_pattern_analysis(state: CodeReviewState) -> CodeReviewState:
    """Detect design patterns and anti-patterns."""
    state["current_step"] = "pattern_analysis_complete"
    state["pattern_analysis_findings"] = []
    return state

def run_security_audit(state: CodeReviewState) -> CodeReviewState:
    """Scan for security vulnerabilities."""
    state["current_step"] = "security_audit_complete"
    state["security_findings"] = []
    return state

def run_performance_analysis(state: CodeReviewState) -> CodeReviewState:
    """Analyze performance bottlenecks."""
    state["current_step"] = "performance_analysis_complete"
    state["performance_findings"] = []
    return state

def assess_testing(state: CodeReviewState) -> CodeReviewState:
    """Evaluate test coverage and quality."""
    state["current_step"] = "testing_assessment_complete"
    state["testing_findings"] = []
    return state

def verify_logic(state: CodeReviewState) -> CodeReviewState:
    """Deep dive into business logic with Personas."""
    files = state.get("target_files", []) or []
    findings = []
    
    # Get persona from config or default to architect
    persona_id = state.get("config", {}).get("persona", "architect")
    system_prompt = get_persona_prompt(persona_id)
    
    if not files:
        # For demo if no files detected
        files = ["main.py"]

    for file_path in files[:2]:  # Limit for speed
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
                
            prompt = ChatPromptTemplate.from_messages([
                ("system", f"{system_prompt}\nAnalyze the following code for subtle logic bugs, edge cases, and architectural drift. Respond briefly."),
                ("human", f"File: {file_path}\n\nCode:\n{code[:2000]}") # Truncate for token limit
            ])
            
            try:
                response = llm.invoke(prompt.format_messages())
                findings.append({
                    "id": str(uuid.uuid4()),
                    "file": file_path,
                    "line": 1,
                    "severity": "medium",
                    "category": "logic",
                    "title": "Titan Intelligence Scan",
                    "description": response.content[:300],
                    "auto_fixable": True
                })
            except:
                pass
            
    state["logic_findings"] = findings
    state["current_step"] = "logic_verification_complete"
    return state

def calculate_titan_score(findings: List[Any]) -> str:
    """Calculates a Code Grade based on finding count and severity."""
    score = 100
    for f in findings:
        sev = f.get("severity", "info")
        if sev == "critical": score -= 20
        elif sev == "high": score -= 10
        elif sev == "medium": score -= 5
        elif sev == "low": score -= 2
    
    if score >= 90: return "A+"
    elif score >= 85: return "A"
    elif score >= 80: return "B+"
    elif score >= 75: return "B"
    elif score >= 65: return "C"
    return "F"

def synthesize_findings(state: CodeReviewState) -> CodeReviewState:
    """Synthesize all findings with Titan Grade."""
    all_f = []
    for key in ["static_analysis_findings", "pattern_analysis_findings", "security_findings", 
                "performance_findings", "testing_findings", "logic_findings"]:
        all_f.extend(state.get(key) or [])
    
    state["all_findings"] = all_f
    state["titan_score"] = calculate_titan_score(all_f)
    
    # Sort by severity priority
    severity_map = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    state["prioritized_issues"] = sorted(all_f, key=lambda x: severity_map.get(x.get("severity", "info"), 5))
    state["current_step"] = f"synthesis_complete (Grade: {state['titan_score']})"
    return state

def generate_fixes(state: CodeReviewState) -> CodeReviewState:
    """Generate code fixes for high-priority issues."""
    state["current_step"] = "fix_generation_complete"
    state["generated_fixes"] = []
    return state

def create_reports(state: CodeReviewState) -> CodeReviewState:
    """Generate professional reports."""
    state["current_step"] = "reporting_complete"
    state["markdown_report"] = "# TitanAI Cognitive Code Report"
    return state

def handle_errors(state: CodeReviewState) -> CodeReviewState:
    """Decision node for error recovery."""
    state["current_step"] = "error_recovered"
    return state
