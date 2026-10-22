# Alpha3 maintenance tests after mandatory review corrections

Exact candidate: [source-candidate-r3.json](source-candidate-r3.json), 26 owned
public files with unchanged Main integration and protected foreign WIP. The prior
independent CODE NO-GO report and all r1 evidence remain unchanged.

| Check in the final clean candidate | Result |
| --- | --- |
| Component/CLI/integration suite with branch instrumentation | 145 passed, 6 skipped, 65 subtests passed |
| Whole repository tests | 523 passed, 7 skipped, 143 subtests passed |
| Ruff lint | PASS |
| Ruff format | PASS, all 17 Python files |
| Strict mypy | PASS, all seven production modules |
| Bandit | PASS, 1883 lines, zero findings/no nosec skips |

New regressions cover both NFC observation orders using actual native identity
primitives, one stored record and idempotent replay with exact originals; bad bytes
followed by ID conflict in both skip modes; source drift with/without a completed
earlier manifest; generator closure after capture; and truthful application failure
evidence. All eight new cases are included in the full runs above. Existing WAL,
concurrency, rollback, restoration, semantic tamper, byte/offset/hash quarantine,
real Windows junction refusal and compatibility assertions continue to pass.

Six component skips need unavailable symbolic-link privilege. The seventh whole
suite skip is the existing QA launcher interpreter-symlink fixture. A real NTFS
junction test executes all five maintenance operations and passes in this suite.

Actual commands, exits, times and log hashes are indexed in
[qa-receipts-r2.json](qa-receipts-r2.json); raw private commands/logs stay in scoped
scratch. [coverage-summary-r2.json](coverage-summary-r2.json) records actual line
and branch denominators. The existing narrow source-bootstrap E402 exemptions
and one existing untyped batch-admission call remain documented in the r1 quality
report. Public release/archive qualification remains pending.
