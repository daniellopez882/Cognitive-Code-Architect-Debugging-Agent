# ADR 0001 — One source tree, one entry point

**Status:** accepted · **Date:** 2026-09-06 (records the decision made in PR #1)

## Context

The repository carried two divergent copies of the same system: a 394-line
tree at the root (`graph.py`, `state.py`, `agents/`, `utils/`) and a 1,422-line
tree under `src/`. They were not in sync. The README documented
`python main.py`; CI ran `python src/main.py`; only the `src/` tree imported
successfully, because the root tree needed a dependency that was never
installed. The tests were written against `src/` and errored at collection.

## Decision

1. `src/` is the implementation. The root duplicates are deleted.
2. `main.py` at the root is a shim that puts `src/` on `sys.path` and calls
   `src/main.py`'s `cli`, so the documented invocation keeps working and there
   is one place the code lives.
3. CI runs `python main.py --help` so the documented entry point is exercised
   on every push, and fails if `pytest` collects nothing.

## Consequences

- One tree to review, one to test, one to package into the image
  (`ENTRYPOINT ["python", "main.py"]`).
- Modules inside `src/` import each other as top-level packages (`agents`,
  `tools`, `utils`, `reporters`), which is why the shim inserts `src/` rather
  than importing `src.main`. A future packaging step would move them under one
  package name; that is a separate decision.
- The shim's `sys.path` insert is the only one in the project and is confined
  to the entry point, so it cannot shadow an installed package from inside the
  library code.
