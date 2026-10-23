# Corrected alpha4 source assurance

Final clean candidate: source-candidate-r10.json, 34 owned public files.
Whole pytest with branch instrumentation: `648 passed, 7 skipped, 6 warnings, 202 subtests passed in 246.62s (0:04:06)`.
All 13 targeted native checks passed, including the unchanged operational
hardening smoke, init/MCP, snapshots/composition, narrowing, workplace catalogue,
index policy, source integrity, multiple roots, containment, empty workplace and
Work context. No filtered native release/archive gate is claimed complete here.

Independent r1 review found four real defects. Seven behavioral cases failed
before correction. The regression file now contains 19 passing cases covering
real file/scan failure and recovery, durable identity around SQL, project counts,
actual resource-event invalidation during collection and terminal publication,
project/global acknowledgement, opaque bytes/publication failures, Main privacy
and safe CLI failures, read-only status/doctor pending state, schema recovery, and
deterministic SQLITE_BUSY between status and SQL at both backend/service layers.
Two status cases, one schema case and two query-race cases have separate retained
red/green receipts. No failing assertion was weakened or broad warning suppressed.

Seven existing environment-dependent skips remain. Six SQLite ResourceWarnings
remain in the whole suite, reported at different existing-test collection points
across runs; origin is not established by that location. Their removal is not
claimed. Feature-only/source fixture checks passed without such warnings.
New-six-module statement coverage: 94.59%; branches:
90.7%; combined: 93.91%. This excludes
the denominator of legacy resource modules and is not a whole-repository claim.

Final behavioral fixtures continue to prove first/repeat refresh opens zero
document bodies on the 1538-document corpus. Earlier r4 timing/open-count reports
remain historical exact evidence for that preserved candidate; no before/after
speed ratio or current r10 timing is invented. Work material validation still
checks the selected actual material separately from derived search availability.

Raw logs, exact command receipts and prior failures remain under owned scratch;
portable hashes are in qa-receipts-r2.json. The original r4 candidate is unchanged.
Installed device, actual connected host and native POSIX remain separate limits.
