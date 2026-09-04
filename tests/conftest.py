"""
Shared test fixtures.

The integration test drives the whole LangGraph workflow, which reaches nodes
that call a chat model. Without a seam those nodes either fail with
``ModuleNotFoundError: No module named 'langchain_google_genai'`` or, with the
package installed, make real billable calls to Google.

``agents.nodes.set_llm`` is that seam. A deterministic fake is installed for
the whole session so the suite is hermetic and free.

The model was previously constructed at module import time, so importing
``agents.nodes`` at all required the provider package and an API key. It is
built on first use now, which is what makes this fixture possible.
"""

from __future__ import annotations

import itertools
import json
import os

import pytest
from langchain_core.messages import AIMessage

os.environ.setdefault("ENVIRONMENT", "testing")

# Broad enough for every node that parses a model response.
DEFAULT_PAYLOAD = {
    "findings": [],
    "issues": [],
    "summary": "Deterministic test response.",
    "severity": "low",
    "verdict": "pass",
    "reasoning": "test",
    "score": 80,
    "recommendations": [],
}


def make_fake_model(payload: str | None = None):
    """
    A real LangChain chat model returning fixed content.

    It must be an actual Runnable: the nodes build ``prompt | llm`` chains, and
    a duck-typed stand-in fails with "Expected a Runnable, callable or dict".
    """
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

    content = payload if payload is not None else json.dumps(DEFAULT_PAYLOAD)
    return GenericFakeChatModel(messages=itertools.cycle([AIMessage(content=content)]))


@pytest.fixture(scope="session", autouse=True)
def _no_live_model_calls():
    """
    Install the fake for the whole session.

    autouse and session-scoped deliberately: no test should be able to reach a
    real provider by accident, and a per-test opt-in would leave that possible.
    """
    from agents import nodes

    nodes.set_llm(make_fake_model())
    yield
    nodes.set_llm(None)


@pytest.fixture
def fake_model():
    """A fresh fake model for a test that wants to control the response."""
    return make_fake_model


@pytest.fixture
def sample_repo(tmp_path):
    """A small Python project on disk, for tests that need real files."""
    (tmp_path / "module.py").write_text(
        "def add(a, b):\n"
        "    return a + b\n"
        "\n"
        "def branchy(x):\n"
        "    if x > 10:\n"
        "        if x > 20:\n"
        "            return 'high'\n"
        "        return 'mid'\n"
        "    return 'low'\n",
        encoding="utf-8",
    )
    return tmp_path
