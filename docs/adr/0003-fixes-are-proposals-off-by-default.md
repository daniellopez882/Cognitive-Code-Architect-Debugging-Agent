# ADR 0003 — Fixes are proposals in the report, never changes to the repository, and asking for them is opt-in

**Status:** accepted · **Date:** 2026-09-06

## Context

Three things were true of "automatic fixes" at once:

- `--auto-fix` defaulted to `True`.
- The graph was compiled with `interrupt_before=["fix_generation"]` "for
  human approval", and the CLI never resumed it. So the default invocation ran
  every analysis stage and then stopped: the reporting node never executed and
  no report was written. The integration test avoided this by passing
  `auto_fix_enabled=False`, with a comment acknowledging the interrupt.
- `generate_fixes_node` did not call a model. It emitted the same placeholder
  for every auto-fixable issue — `# Fixed <title>\ndef fixed_function():\n    pass`
  — checked that it parsed, and labelled it `valid_syntax`. The reporter then
  ignored fixes entirely, so nobody ever saw the placeholder either.

`tools/git_operations.py` still has `create_fix_branch` and `commit_and_push`;
nothing in the graph calls them.

## Decision

1. **Off by default.** `--auto-fix` is opt-in; its help text says what it does
   and does not do. A test inspects the click option and CI repeats the check.
2. **The model proposes.** `propose_fix` sends the finding and the surrounding
   lines of the file to the model and asks for one fenced `python` block. The
   block is parsed with `ast`; the record carries `status` (`proposed`,
   `invalid_syntax`, `no_code_block`) and `applied: False`. A provider failure
   is recorded in `errors` and the report is still written.
3. **Nothing is applied.** No node writes to the repository under review, and a
   test asserts the file is byte-identical after a proposal is made. The
   `commit_and_push` helper stays in `tools/` unused; wiring it would be a new
   ADR with a human approval step that actually exists.
4. **Proposals appear in the report** — a "Proposed fixes (not applied)"
   section in the Markdown, `proposed_fixes` and `fixes_applied: false` in the
   JSON — and the summary counts how many were usable.
5. **The interrupt is gone.** There is nothing to approve because nothing is
   applied; a run with `--auto-fix` now reaches the report.

## Consequences

- The default run writes a report. A run with `--auto-fix` writes a report with
  proposals, costs one model call per auto-fixable finding, and changes no file.
- Proposals are untrusted output about untrusted input: a reviewed file can try
  to steer the model. Because nothing is applied, the blast radius is a bad
  suggestion in a report a human reads.
- `auto_fixable` is set by the analysis nodes and is generous (the logic review
  marks every file it comments on); the number of proposals — and model calls —
  is bounded by the number of findings, not by a budget. A cap is future work.
