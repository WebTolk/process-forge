# f0304-evidence worker log

## 2026-09-10 — worker-f0304-evidence

- Scope: F03/F04 latest applicable evidence, saved-file freshness, and portable regression smoke.
- Files changed: `src/processforge_core/process_execution.py`; `tools/smoke_work_evidence_freshness.py`.
- Files analyzed: bounded brief, F03/F04 audit report and reproduction reference, process-execution smoke support and related transition smokes.
- Implementation: identity-first selection now evaluates the latest applicable record before status; input/artifact aliases share identity; `evidence_id` participates in merge identity; selected file-backed evidence is safely resolved and rehashed for state/readiness/transition dependencies; diagnostics are explicit and read-only; current stage evidence still resets on re-entry; run-completion gate diagnostics are retained.
- Checks: `git diff --check` passed for the modified core file. Existing transition smoke execution was attempted through the permitted temporary PF fixture, but stopped after the first documented Windows `TemporaryDirectory` cleanup failure (`WinError 5`, with a subprocess UTF-8 reader exception preceding it). No further execution experiments were run.
- Residual risk: genuine smoke execution and before/after comparison remain for primary because the local Windows temporary-directory ACL/handle failure prevented fixture cleanup. File hashing retains the normal TOCTOU window documented in the brief.

## 2026-09-10 — static follow-up

- Scope: reviewed the new smoke for pinned-process integrity after its run-completion fixture mutation; updated the fixture to recompute the pinned definition fingerprint. Hardened safe-path normalization against malformed path values. No additional execution was attempted after the documented temporary-directory failure.
