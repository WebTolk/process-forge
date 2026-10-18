# F03/F05 Independent Assurance Report

## Verdict

**PASS — bounded assurance.** No concrete implementation regression was found in the final source under the stated contract. This is not full release qualification.

## Primary evidence reviewed

- F03/F04 final smoke: `f0304-final.json`, exit `0`; output: `PASS: Work evidence identity and file freshness`.
- F03/F04 extracted-copy proof: portable exit `0`; baseline exit `1`.
- F05 final matrix: `f05-matrix-2.json`, exit `0`; all 18 before/after fault points passed, plus malformed-journal and recovery checks.
- F05 extracted-copy proof: portable exit `0`; baseline exit `1`.
- Final terminal and event smokes: both exit `0`.
- Ten related checks: all exit `0`.
- Public cleanliness, preservation, checksum, and diff checks: passed.
- Earlier `f05-matrix-1`, `f05-matrix-final`, and isolated-final failures were correctly treated as rejected candidates.

## Source review

Reviewed `src/processforge_core/process_execution.py` and both F03/F05 smoke tools.

- Completion-intent loading precedes the terminal short-circuit (`process_execution.py:404-414`).
- The intent is written before replay (`process_execution.py:534-535`).
- Replay restores assignment/run payloads, summaries, handoff, task index, projection, and deterministic event IDs (`process_execution.py:1252+`).
- Journal validation checks identity, ownership paths, terminal statuses, process pin, and fingerprint (`process_execution.py:1186+`).
- Evidence selection uses latest applicable records, alias-aware identity, current-stage reset semantics, safe paths, and SHA-256 freshness diagnostics.
- Required inputs use accumulated evidence while produced artifacts and required evidence use current-stage evidence.

The F05 matrix genuinely covers `run`, `intent`, `assignment`, `summary`, `handoff`, `index`, `projection`, `event`, and cleanup failures both before and after the targeted write. The generic atomic-write hook also covers the intent path.

## Worker checks

No runtime fixture or smoke suite was rerun by this worker, per the bounded-assurance instructions and prior documented Windows `TemporaryDirectory` `WinError 5` limitation. Static source/diff inspection, raw-artifact review, AST parsing, and Git-history inspection were performed.

Git-history origin recorded in the handoff: `b5d3e32`, `0914c52`, `4d1d91e`, `1494638`.

## Residual limits

- File-backed evidence retains the normal TOCTOU window between validation and later use.
- Completion-intent fingerprints are unkeyed. A party able to edit the journal and recompute its fingerprint could alter journal content or event specifications; the supplied tests establish corruption/mismatch rejection, not adversarial tamper resistance.
- Hook delivery remains bounded at-least-once, not exactly-once.
- F06–F12, baseline Runtime startup, and full release qualification remain outside this assurance scope.