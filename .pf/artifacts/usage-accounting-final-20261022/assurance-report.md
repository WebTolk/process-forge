# Assurance: PASS

2026-10-22. Integrated candidate accepted after independent review and remediation.
Primary registered QA: 68 tests and 36 subtests PASS, Ruff lint/format over 14
Python files PASS, mypy over 11 source modules PASS with --follow-imports=silent.
Existing codex-exec worker, prepared worker-governance and conversation-completeness
smokes PASS; driver smoke repeated after the clock fix. No whole-repository type
debt cleanup was claimed or included. Staged HEAD-based facade imports and usage
parser registration were also checked independently of unrelated facade WIP.

First native independent review: two reproduced P2 findings, preserved in
../usage-accounting-review-20261022/report.md. Primary corrections added explicit
timestamp type validation and paired clock sampling without I/O. A separate native
re-review returned PASS with 12 checks, independently reproducing both corrected
cases, prefix recovery, open/final timing replay and unchanged exit/report behavior.
All four corrected file hashes and the other 13 original candidate hashes matched.
Both reviewers recorded actual PF Python/OOP reads with matching source hashes.

Real receipt qualification: both completed review attempts were automatically
captured by the managed Codex driver and matched the common database. The final
re-review receipt reports input=508754, output=6421, cache-read=452096,
cache-write=0, reasoning-output=631; total=515175. Cache/reasoning were not added
again. Execution=228.076003 seconds; observed UTC span=228.076023 seconds, with
the small clock difference explicitly reported rather than hidden.

For each attempt, two CLI replay operations stored zero usage and zero activity
facts. Per-attempt facts, counts, token totals and durations remained identical;
project totals also remained unchanged. Collection observation freshness advanced
as expected. See the two *-qualification.json files for exact source hashes and
results; raw source streams remain private runtime evidence.

Test plan/case mapping: test-plan.md. Initial QA: qa-public.json. Final changed
scope QA: remediation-qa.json. Frozen initial and remediation byte manifests are
retained separately; no approved input/report was rewritten to conceal findings.

Limits: source checkout acceptance, no archive/installed/connected-host claim.
Crash behavior is tested through an absent finalizer, not a physical host crash.
Modern Kimi is explicit qualified import plus synthetic tests, not native automatic
capture. Historical attempts and agent activity outside supported capture remain
unknown. Coverage stays partial; usage time without a native timestamp uses its
pinned observation with partial quality. Prototype pre-amendment core-fix facts
were not silently rewritten. No money, UI, plugin or REST implementation.
