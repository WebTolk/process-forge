# F03/F04 evidence implementation report

## Result

Implemented bounded F03/F04 fixes in `src/processforge_core/process_execution.py` and added the portable MCP-driven regression matrix in `tools/smoke_work_evidence_freshness.py`.

## Source changes

- Latest applicable evidence is selected by identity before status evaluation.
- Input/artifact aliases share identity; `evidence_id` is honored during merges.
- Selected file-backed evidence is safely resolved and checked for regular-file status and matching SHA-256.
- Missing, changed, unsafe, unreadable, and missing-digest cases produce explicit diagnostics without mutating stored history.
- Current-stage evidence resets on re-entry.
- Run-completion gate blockers include freshness diagnostics.

## Regression coverage

The smoke covers historical PASS followed by FAIL, recovery, cross-kind supersession, unrelated IDs, re-entry output reset, changed/deleted files, digest resubmission, obsolete-file isolation, run-completion gate freshness, unsafe/missing-digest diagnostics, read-only state, and normal completion.

## Checks

- `git diff --check -- src/processforge_core/process_execution.py`: passed.
- Existing transition smoke execution was attempted but stopped after the documented Windows `TemporaryDirectory` `WinError 5` cleanup failure. No smoke PASS is claimed.

Residual risk: genuine smoke execution and before/after comparison remain for primary validation. File hashing retains the normal TOCTOU window.