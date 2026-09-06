from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

# Node functions
# The 12 node functions were defined *here* as stubs -- placeholders that set a
# status string and returned -- shadowing the real implementations in
# agents/nodes.py. graph.py never imported nodes.py, so the workflow wired the
# stubs and the 300 lines of actual analysis in nodes.py were dead code.
#
# The most visible symptom: create_reports_node returned a two-line placeholder
# string instead of calling MarkdownReporter, and left current_step at
# "creating_reports", so a completed run never signalled completion.
from agents.nodes import (
    assess_testing_node,
    create_reports_node,
    define_scope_node,
    generate_fixes_node,
    initialize_repository_node,
    run_pattern_analysis_node,
    run_performance_analysis_node,
    run_security_audit_node,
    run_static_analysis_node,
    synthesize_findings_node,
    verify_logic_node,
    verify_policy_node,
)
from agents.state import CodeReviewState


def should_generate_fixes(state: CodeReviewState) -> str:
    """Determine if fixes should be generated."""
    if not state.get("auto_fix_enabled", False):
        return "skip_fixes"
    return "generate_fixes"


# Create the graph
def create_code_review_graph():
    workflow = StateGraph(CodeReviewState)

    # Add Nodes
    workflow.add_node("initialization", initialize_repository_node)
    workflow.add_node("scope_definition", define_scope_node)
    workflow.add_node("static_analysis", run_static_analysis_node)
    workflow.add_node("pattern_analysis", run_pattern_analysis_node)
    workflow.add_node("security_audit", run_security_audit_node)
    workflow.add_node("performance_analysis", run_performance_analysis_node)
    workflow.add_node("testing_assessment", assess_testing_node)
    workflow.add_node("logic_verification", verify_logic_node)
    workflow.add_node("policy_verification", verify_policy_node)
    workflow.add_node("synthesis", synthesize_findings_node)
    workflow.add_node("fix_generation", generate_fixes_node)
    workflow.add_node("reporting", create_reports_node)

    # Set Edges
    workflow.set_entry_point("initialization")
    workflow.add_edge("initialization", "scope_definition")
    workflow.add_edge("scope_definition", "static_analysis")
    workflow.add_edge("static_analysis", "pattern_analysis")
    workflow.add_edge("pattern_analysis", "security_audit")
    workflow.add_edge("security_audit", "performance_analysis")
    workflow.add_edge("performance_analysis", "testing_assessment")
    workflow.add_edge("testing_assessment", "logic_verification")
    workflow.add_edge("logic_verification", "policy_verification")
    workflow.add_edge("policy_verification", "synthesis")

    # Conditional edge: propose fixes only when asked (--auto-fix)
    workflow.add_conditional_edges(
        "synthesis",
        should_generate_fixes,
        {"generate_fixes": "fix_generation", "skip_fixes": "reporting"},
    )
    workflow.add_edge("fix_generation", "reporting")
    workflow.add_edge("reporting", END)

    # Compile with a checkpointer (per-thread state).
    #
    # interrupt_before=["fix_generation"] used to sit here "for user approval".
    # The CLI never resumed the graph, so with --auto-fix -- the default at the
    # time -- every run stopped after synthesis and no report was written.
    # Nothing applies a fix, so there is nothing to approve: proposals go into
    # the report for a human to read.
    memory = MemorySaver()
    return workflow.compile(
        checkpointer=memory,
    )


app = create_code_review_graph()
