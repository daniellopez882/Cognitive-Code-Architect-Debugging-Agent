"""
The command line can review a directory or a URL.

Reproduced defect: ``review`` passed ``local_path=""`` for every target, so the
initialisation node cloned into an empty path and raised ``FileNotFoundError``
before any analysis ran -- for a URL and a directory alike. The CLI could not
review anything; the integration test bypassed it, and the initialisation node
then discarded the fixture directory in favour of ".", so that test analysed
this repository's own tree.
"""

from __future__ import annotations

import json
import os

from click.testing import CliRunner

from agents import nodes
from main import cli, resolve_target


class TestResolveTarget:
    def test_an_existing_directory_is_reviewed_in_place(self, sample_repo):
        url, local_path, temporary = resolve_target(str(sample_repo))
        assert url == "local"
        assert local_path == os.path.abspath(str(sample_repo))
        assert temporary is False

    def test_anything_else_gets_a_fresh_temporary_directory(self):
        url, local_path, temporary = resolve_target("https://example.invalid/some/repo.git")
        try:
            assert url == "https://example.invalid/some/repo.git"
            assert os.path.isdir(local_path)
            assert temporary is True
        finally:
            os.rmdir(local_path)


class TestInitialisationKeepsThePath:
    def test_the_given_local_path_survives(self, sample_repo):
        state = {"repository_url": "local", "local_path": str(sample_repo), "errors": []}
        out = nodes.initialize_repository_node(state)
        assert out["local_path"] == str(sample_repo)

    def test_an_empty_path_means_the_working_directory(self):
        """The CLI used to pass "" for every target."""
        state = {"repository_url": "local", "local_path": "", "errors": []}
        assert nodes.initialize_repository_node(state)["local_path"] == "."


class TestReviewCommand:
    def test_a_directory_is_reviewed_and_a_report_written(self, sample_repo, tmp_path):
        out_dir = tmp_path / "reports"
        result = CliRunner().invoke(
            cli,
            ["review", str(sample_repo), "--output", str(out_dir), "--format", "json"],
        )
        assert result.exit_code == 0, result.output
        reports = list(out_dir.glob("*.json"))
        assert reports, result.output
        data = json.loads(reports[0].read_text(encoding="utf-8"))
        assert data["fixes_applied"] is False
        assert "findings" in data
        # Findings point at the fixture, not at this repository.
        for finding in data["findings"]:
            assert str(sample_repo) in finding.get("file", str(sample_repo))

    def test_a_failed_run_exits_non_zero(self, sample_repo, tmp_path, fake_model):
        class Exploding:
            def invoke(self, messages):
                raise RuntimeError("provider down")

        nodes.set_llm(Exploding())
        try:
            result = CliRunner().invoke(
                cli, ["review", str(sample_repo), "--output", str(tmp_path / "r")]
            )
        finally:
            nodes.set_llm(fake_model())
        assert result.exit_code == 1
        assert "Error during analysis" in result.output
