"""
Fixes are model proposals in the report, never changes to the repository, and
asking for them is opt-in.

Reproduced defects:

* ``--auto-fix`` defaulted to True and routed the run into
  ``interrupt_before=["fix_generation"]``, which the CLI never resumed. The
  default invocation stopped after synthesis and wrote no report.
* ``generate_fixes_node`` emitted the same placeholder for every issue --
  ``def fixed_function():\\n    pass`` -- labelled ``valid_syntax``, and the
  reporter ignored fixes entirely, so nobody ever saw them.
"""

from __future__ import annotations

import pytest

from agents import nodes
from agents.graph import app
from reporters.markdown_reporter import MarkdownReporter

FINDING = {
    "id": "f-1",
    "file": "",
    "line": 1,
    "severity": "medium",
    "category": "logic",
    "title": "Off-by-one in add",
    "description": "add returns a + b + 1",
    "recommendation": "Return a + b",
    "auto_fixable": True,
}

GOOD_REPLY = "Here is the corrected code:\n```python\ndef add(a, b):\n    return a + b\n```\nDone."
BAD_SYNTAX_REPLY = "```python\ndef add(a, b:\n    return a + b\n```"


def _state(repo_dir, auto_fix):
    return {
        "repository_url": "local",
        "local_path": str(repo_dir),
        "review_scope": "full",
        "severity_threshold": "low",
        "auto_fix_enabled": auto_fix,
        "messages": [],
        "errors": [],
        "static_analysis_findings": [],
        "pattern_analysis_findings": [],
        "security_findings": [],
        "performance_findings": [],
        "testing_findings": [],
        "logic_findings": [],
        "files_analyzed": 0,
        "total_files": 0,
        "all_findings": [],
        "prioritized_issues": [],
        "quick_wins": [],
        "generated_fixes": [],
        "markdown_report": "",
        "json_report": {},
        "github_issues": [],
        "current_step": "started",
        "analysis_start_time": 0.0,
        "user_feedback": [],
        "skip_categories": [],
    }


@pytest.fixture
def model(fake_model):
    """Install a controllable fake for one test, then restore the session fake."""

    def install(reply: str):
        nodes.set_llm(fake_model(reply))

    yield install
    nodes.set_llm(fake_model())


class TestOptIn:
    def test_the_cli_does_not_propose_fixes_unless_asked(self):
        from main import cli

        option = next(p for p in cli.commands["review"].params if p.name == "auto_fix")
        assert option.default is False

    async def test_a_run_with_fixes_enabled_reaches_the_report(self, sample_repo):
        """With the interrupt in place this stopped at synthesis and wrote nothing."""
        final = _state(sample_repo, auto_fix=True)
        async for event in app.astream(final, {"configurable": {"thread_id": "t-fixes"}}):
            for _node, delta in event.items():
                final.update(delta)
        assert "reporting_complete" in final["current_step"]
        assert final["markdown_report"].startswith("# Code Review Report")
        assert final["json_report"]["fixes_applied"] is False
        # The session fake answers JSON, not code, so every proposal is unusable
        # and says so rather than pretending.
        assert final["generated_fixes"]
        assert {p["status"] for p in final["generated_fixes"]} == {"no_code_block"}
        assert "Proposed fixes (not applied)" in final["markdown_report"]

    async def test_a_run_without_fixes_has_no_proposals(self, sample_repo):
        final = _state(sample_repo, auto_fix=False)
        async for event in app.astream(final, {"configurable": {"thread_id": "t-nofix"}}):
            for _node, delta in event.items():
                final.update(delta)
        assert "reporting_complete" in final["current_step"]
        assert final["generated_fixes"] == []
        assert "Proposed fixes" not in final["markdown_report"]


class TestProposals:
    def test_a_code_block_becomes_a_proposal(self, model):
        model(GOOD_REPLY)
        record = nodes.propose_fix(FINDING)
        assert record["status"] == "proposed"
        assert record["proposed_code"] == "def add(a, b):\n    return a + b"
        assert record["applied"] is False
        assert record["issue_id"] == "f-1"

    def test_invalid_syntax_is_flagged_not_trusted(self, model):
        model(BAD_SYNTAX_REPLY)
        record = nodes.propose_fix(FINDING)
        assert record["status"] == "invalid_syntax"

    def test_no_code_block_is_a_clean_result(self, model):
        model("I would change the return statement.")
        record = nodes.propose_fix(FINDING)
        assert record["status"] == "no_code_block"
        assert record["proposed_code"] is None

    def test_the_old_placeholder_is_gone(self, model):
        model(GOOD_REPLY)
        assert "fixed_function" not in nodes.propose_fix(FINDING)["proposed_code"]

    def test_the_repository_is_never_written(self, sample_repo, model):
        model(GOOD_REPLY)
        target = sample_repo / "module.py"
        before = target.read_text(encoding="utf-8")
        finding = {**FINDING, "file": str(target), "line": 2}
        record = nodes.propose_fix(finding)
        assert record["status"] == "proposed"
        assert target.read_text(encoding="utf-8") == before

    def test_the_snippet_sent_to_the_model_comes_from_the_file(self, sample_repo):
        target = sample_repo / "module.py"
        snippet = nodes._snippet_for({"file": str(target), "line": 2})
        assert "def add(a, b):" in snippet

    def test_a_provider_failure_does_not_sink_the_report(self, fake_model):
        class Exploding:
            def invoke(self, messages):
                raise RuntimeError("provider down")

        nodes.set_llm(Exploding())
        try:
            state = {"prioritized_issues": [FINDING], "errors": [], "config": {}}
            out = nodes.generate_fixes_node(state)
        finally:
            nodes.set_llm(fake_model())
        assert out["generated_fixes"] == []
        assert out["current_step"] == "fix_generation_complete"
        assert any("provider down" in e for e in out["errors"])


class TestReport:
    def test_proposals_are_marked_not_applied(self):
        report = MarkdownReporter().generate(
            [FINDING],
            [
                {
                    "issue_id": "f-1",
                    "title": "Off-by-one in add",
                    "file": "module.py",
                    "line": 1,
                    "proposed_code": "def add(a, b):\n    return a + b",
                    "status": "proposed",
                    "applied": False,
                },
                {
                    "issue_id": "f-2",
                    "title": "Other",
                    "file": "x.py",
                    "line": 3,
                    "status": "no_code_block",
                },
            ],
        )
        assert "## Proposed fixes (not applied)" in report
        assert "Nothing was written to the repository" in report
        assert "def add(a, b):" in report
        assert "No usable proposal (no_code_block)" in report

    def test_no_proposals_means_no_section(self):
        report = MarkdownReporter().generate([FINDING])
        assert "Proposed fixes" not in report
