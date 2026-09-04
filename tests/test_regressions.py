"""
Regression tests for the defects found while making this suite runnable.

Before this work the suite could not be collected at all: every test errored on
imports, because the tests were written against the `src/` layout and nothing
put it on the path. Once they ran, five real bugs surfaced in sequence.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from tools.code_analysis import calculate_cyclomatic_complexity, detect_code_smells

SRC = Path(__file__).resolve().parents[1] / "src"


def _called_names(source: str) -> set[str]:
    """
    Every callable name invoked in a block of source.

    Text searches match the comments that explain a fix, so these assertions
    look at what the code actually calls.
    """
    import ast
    import textwrap

    names: set[str] = set()

    def render(node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{render(node.value)}.{node.attr}"
        return ""

    for node in ast.walk(ast.parse(textwrap.dedent(source))):
        if isinstance(node, ast.Call):
            rendered = render(node.func)
            if rendered:
                names.add(rendered)
    return names


class TestComplexityUsesTheLibrary:
    """
    calculate_cyclomatic_complexity shelled out to a `radon` executable. radon
    is a declared dependency, but installing the library does not put its
    console script on PATH in every environment -- and it was absent here. The
    call raised FileNotFoundError into a bare `except Exception`, so the tool
    silently reported no complexity rather than failing.

    A second bug hid behind it: the result was read with
    `data.get(file_path, [])`, which needs radon to echo the path back
    byte-identically. On Windows it does not.
    """

    def test_complexity_is_reported(self, tmp_path):
        f = tmp_path / "branchy.py"
        f.write_text(
            "def f(x):\n"
            "    if x > 10:\n"
            "        if x > 20:\n"
            "            if x > 30:\n"
            "                return 'high'\n"
            "            return 'mid-high'\n"
            "        return 'mid'\n"
            "    return 'low'\n",
            encoding="utf-8",
        )
        data = calculate_cyclomatic_complexity.invoke({"file_path": str(f)})["complexity_data"]
        assert len(data) > 0
        assert data[0]["complexity"] >= 4

    def test_no_subprocess_is_spawned(self):
        """
        Checked against the AST, not the text: the explanatory comments in the
        source mention subprocess, so a substring search matches its own
        documentation.
        """
        calls = _called_names(inspect.getsource(calculate_cyclomatic_complexity.func))
        assert not any(name.startswith("subprocess.") for name in calls), (
            f"complexity should use radon as a library, found: {sorted(calls)}"
        )

    def test_each_entry_carries_a_name_and_rank(self, tmp_path):
        f = tmp_path / "m.py"
        f.write_text("def a():\n    return 1\n", encoding="utf-8")
        entry = calculate_cyclomatic_complexity.invoke({"file_path": str(f)})["complexity_data"][0]
        assert entry["name"] == "a"
        assert entry["rank"]

    def test_a_file_that_does_not_parse_is_reported_not_raised(self, tmp_path):
        f = tmp_path / "broken.py"
        f.write_text("def (:\n", encoding="utf-8")
        result = calculate_cyclomatic_complexity.invoke({"file_path": str(f)})
        assert result["complexity_data"] == []
        assert "syntax error" in result["error"]

    def test_a_missing_file_is_reported_not_raised(self, tmp_path):
        result = calculate_cyclomatic_complexity.invoke({"file_path": str(tmp_path / "nope.py")})
        assert result["complexity_data"] == []
        assert result["error"]


class TestNonAsciiSources:
    """
    Files were opened with `open(path, 'r')`, taking the platform default
    encoding -- cp1252 on Windows. Any UTF-8 source with a non-ASCII byte
    raised UnicodeDecodeError, so a code-review tool crashed on the code it
    was asked to review.
    """

    def test_a_utf8_source_can_be_analysed(self, tmp_path):
        f = tmp_path / "unicode.py"
        f.write_text(
            "# Ünïcödé comment — with an em dash and “smart quotes”\n"
            "def greet():\n"
            '    return "café 日本語"\n',
            encoding="utf-8",
        )
        result = calculate_cyclomatic_complexity.invoke({"file_path": str(f)})
        assert result["complexity_data"], result.get("error")

    def test_every_open_call_declares_an_encoding(self):
        """Guards against the platform default creeping back in."""
        offenders = []
        for path in SRC.rglob("*.py"):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "open(" in line and "encoding=" not in line and ".open(" not in line:
                    offenders.append(f"{path.relative_to(SRC)}:{number}")
        assert not offenders, f"open() without an explicit encoding: {offenders}"


class TestErrorSentinels:
    """
    The analysis tools signal failure by returning `[{"error": ...}]` in the
    same list as real results. run_pattern_analysis_node treated every entry as
    a finding and crashed on `smell.get("type").replace(...)`, because an error
    entry has no "type".
    """

    def test_a_missing_file_yields_an_error_entry_not_a_crash(self, tmp_path):
        result = detect_code_smells.invoke({"file_path": str(tmp_path / "absent.py")})
        assert isinstance(result, list)
        assert result and "error" in result[0]

    def test_the_node_skips_error_entries(self):
        from agents.nodes import run_pattern_analysis_node

        source = inspect.getsource(run_pattern_analysis_node)
        assert 'if "error" in smell' in source

    def test_the_node_survives_an_error_entry(self, tmp_path):
        from agents.nodes import run_pattern_analysis_node

        state = {
            "target_files": [str(tmp_path / "does_not_exist.py")],
            "errors": [],
        }
        out = run_pattern_analysis_node(state)
        assert out["current_step"] == "pattern_analysis_complete"
        assert out["errors"], "the failure should be recorded, not swallowed"


class TestPromptConstruction:
    """
    verify_logic_node interpolated the reviewed file's source into a
    ChatPromptTemplate with an f-string. The template reads { and } as variable
    delimiters, so any file containing a dict literal, an f-string or a set
    raised KeyError -- which is most real Python. It was also an injection
    path, since file content became part of the template itself.
    """

    def test_the_node_does_not_template_file_content(self):
        """AST, not text: the comments explaining the fix name the class."""
        from agents.nodes import verify_logic_node

        source = inspect.getsource(verify_logic_node)
        calls = _called_names(source)
        assert not any("ChatPromptTemplate" in name for name in calls), (
            f"file content must not go through a prompt template: {sorted(calls)}"
        )
        assert {"SystemMessage", "HumanMessage"} <= calls

    def test_code_containing_braces_is_reviewed_without_raising(self, tmp_path):
        from agents.nodes import verify_logic_node

        f = tmp_path / "braces.py"
        f.write_text(
            'CONFIG = {"generate_fixes": True, "skip": {"a", "b"}}\n'
            'def f(n):\n    return f"value: {n}"\n',
            encoding="utf-8",
        )
        state = {"target_files": [str(f)], "errors": [], "config": {}}
        out = verify_logic_node(state)
        assert out["current_step"] == "logic_verification_complete"
        assert out["logic_findings"]


class TestGraphWiresTheRealNodes:
    """
    graph.py defined its own 12 stub nodes, shadowing the implementations in
    nodes.py, and never imported them. The workflow ran placeholders while 300
    lines of real analysis sat unused -- create_reports_node returned a literal
    placeholder string instead of calling MarkdownReporter, and left
    current_step at "creating_reports" so a run never signalled completion.
    """

    def test_graph_imports_the_node_implementations(self):
        source = (SRC / "agents" / "graph.py").read_text(encoding="utf-8")
        assert "from agents.nodes import" in source

    def test_graph_defines_no_node_functions_of_its_own(self):
        source = (SRC / "agents" / "graph.py").read_text(encoding="utf-8")
        defined = [
            line for line in source.splitlines() if line.startswith("def ") and "_node" in line
        ]
        assert not defined, f"graph.py still shadows node implementations: {defined}"

    def test_the_wired_report_node_is_the_real_one(self):
        from agents import graph, nodes

        assert graph.create_reports_node is nodes.create_reports_node

    @pytest.mark.parametrize(
        "name",
        [
            "initialize_repository_node",
            "define_scope_node",
            "run_static_analysis_node",
            "run_pattern_analysis_node",
            "synthesize_findings_node",
            "create_reports_node",
        ],
    )
    def test_every_wired_node_comes_from_nodes_module(self, name):
        from agents import graph, nodes

        assert getattr(graph, name) is getattr(nodes, name)


class TestModelIsLazy:
    """
    nodes.py constructed ChatGoogleGenerativeAI at module import time, so
    importing it required the provider package and an API key before any node
    had run -- and left no seam for tests.
    """

    def test_the_module_imports_without_credentials(self):
        import agents.nodes as nodes

        assert hasattr(nodes, "get_llm")

    def test_a_replacement_model_can_be_installed(self):
        from agents import nodes

        original = nodes._llm
        sentinel = object()
        try:
            nodes.set_llm(sentinel)
            assert nodes.get_llm() is sentinel
        finally:
            nodes.set_llm(original)

    def test_the_conftest_fake_is_active(self):
        from agents import nodes

        assert type(nodes.get_llm()).__name__ == "GenericFakeChatModel"
