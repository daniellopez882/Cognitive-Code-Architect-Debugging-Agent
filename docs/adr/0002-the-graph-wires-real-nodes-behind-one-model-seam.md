# ADR 0002 — The graph wires the real nodes, behind one model seam

**Status:** accepted · **Date:** 2026-09-06 (records the decision made in PR #1)

## Context

`graph.py` defined twelve stub nodes of its own with the same names as the
implementations in `nodes.py`, and wired the stubs. About three hundred lines of
real analysis — pylint, complexity, pattern detection, the model-backed logic
review — were unreachable. The stubs returned fixed values, so the tool produced
a report that looked like a review and was not one.

`nodes.py` also built its Google model at import time, so importing the module
at all needed `langchain_google_genai` installed and a key present. No test
could import the graph without credentials, and any test that did would have
made billable calls.

## Decision

1. `graph.py` imports the node functions from `nodes.py` and defines none of
   its own. CI reads `graph.py` and fails if it stops importing
   `agents.nodes` or defines a `*_node` function again.
2. `nodes.get_llm()` builds the model on first use; `nodes.set_llm()` is the
   seam. `tests/conftest.py` installs a deterministic
   `GenericFakeChatModel` for the whole session, so the suite is hermetic and
   free; the integration test drives the whole graph through it.
3. Reviewed source is passed to the model as message content, never
   interpolated into a `ChatPromptTemplate`. The template treats `{` and `}` as
   variable delimiters, so any file with a dict literal or an f-string raised
   `KeyError` and the reviewer crashed on most real Python; it was also an
   injection path, because file content became part of the template itself.
   The system prompt tells the model the code is untrusted input.
4. Complexity is computed through `radon` as a library. It was invoked as a
   CLI that was not on `PATH`, and the failure was swallowed by a bare
   `except`, so complexity silently reported nothing.

## Consequences

- The graph can be imported, wired and driven end to end in a test without a
  provider package or a key; the first real model call is the first place a
  missing `GOOGLE_API_KEY` is felt.
- The logic-review node still turns the model's whole reply into one finding
  per file (`description=response.content[:200]`); parsing structured findings
  out of the reply is future work and is stated as such in the README.
- Anything that needs the model in a test controls the reply through
  `set_llm`, and restores the session fake afterwards.
