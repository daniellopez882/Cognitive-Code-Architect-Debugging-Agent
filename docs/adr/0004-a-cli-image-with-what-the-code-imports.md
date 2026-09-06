# ADR 0004 — A command-line image, built from what the code imports

**Status:** accepted · **Date:** 2026-09-06

## Context

There was no image. `requirements.txt` pinned about thirty packages — `semgrep`,
`py-spy`, `safety`, `tree-sitter` and its grammars, `reportlab`, `PyGithub`,
`python-gitlab`, `black`, `flake8`, `mypy`, `memory-profiler`, `jinja2`,
`tenacity`, `astroid`, `coverage` — and the code imports none of them. The
pull request's `requirements-dev.txt` already avoided the runtime file for that
reason, listing "what the tests actually import" by hand, which meant two lists
to keep in step.

## Decision

1. `requirements.txt` lists what `src/` imports plus `pylint`, which
   `run_pylint` invokes as a subprocess: `langgraph`, `langchain-core`,
   `langchain-google-genai`, `gitpython`, `radon`, `pylint`, `rich`, `click`,
   `python-dotenv`, `pyyaml`. `requirements-dev.txt` is `-r requirements.txt`
   plus the test and lint tooling. A test fails if a declared runtime
   dependency is imported nowhere.
2. The image is two-stage, `python:3.12-slim`, with `git` installed because
   GitPython shells out to it. It runs as uid 10001 with
   `ENTRYPOINT ["python", "main.py"]` and `CMD ["--help"]`; reports go to
   `/app/reports`, declared as a volume.
3. CI builds the image, runs `--help` and `review --help` in it (a CLI image has
   no port to probe; importing the graph is the boot check), and asserts the
   uid is not 0.
4. `GOOGLE_API_KEY` is read at the first model call, not at start, so the image
   starts, prints help and runs the static stages without it.

## Consequences

- The install is a fraction of the old one and matches the code. Adding a tool
  that needs `semgrep` means adding `semgrep` back, deliberately, with the code
  that imports it.
- `tools/test_generator.py` imports `pytest` and is imported by nothing; it is
  dead code and excluded from the runtime set on purpose. Removing it is a
  separate cleanup.
- Reports written inside the container belong to uid 10001; mount
  `/app/reports` to a directory that user can write.
