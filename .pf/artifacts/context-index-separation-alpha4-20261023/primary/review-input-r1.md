# Independent native review: alpha4 context/index separation

Implementation is complete and source QA is recorded. Review ONLY the canonical
candidate tree from source-candidate-r4.json. Open candidate/path for every
manifest entry and verify its hashes before and after review. main-owned.diff
contains the exact Main delta from the accepted base. The outer working Main has
foreign paused OOP changes: do not use it as the release candidate.

Read current architecture-r2.md, storage-decision-r3.md, trigger-policy-r4.md,
domain.md, original-task-at-admission.yaml, actual PF Python excerpts/provenance
and guidance. R2/R3/R4 explicitly supersede earlier initial Runtime timer design:
NO periodic timer/thread/loop in alpha4; a cold callable invokes the same owner
as CLI. Existing SQLite FTS5 storage stays. A narrow actual backend Protocol is a
seam, not a claim that configurable MySQL/vector/RAG backends already exist.

Read all 32 owned public files, test-report-r1.md, code-quality-report-r1.md,
qa-receipts-r1.json and coverage-summary-r1.json. Assess contracts and risks,
including new CLI text/failure surfaces and six retained SQLite warnings. Use
project-local file reads and optional stdlib fixture checks in your own scratch.
Do not run Git, PF lifecycle, external QA, install tools, access live workplace
roots, operate services or start other agents. Primary owns orchestration and
registered tools. Emit a real READ_ACK after reading the inputs.

Focus: no hidden indexing from init/refresh/repair/context/search/mutation hooks;
required resource validation/access/metadata-only/count/error/pagination contracts;
one application owner for explicit CLI and job, strict project vs workplace scope;
read-only SQLite connections do not create/write/wait, URI safety and WAL readers;
bounded cross-process writer coordination, atomic durable state/report failures,
crash/interruption retry and no false ready; private-path-safe errors, fresh state
races; constructor/import side effects and OOP dependency direction; meaningful
tests and accurate EN/RU docs. Distinguish actual defects from documented deferred
scheduler/backends/installed/host/POSIX scope limits.

Report each defect with severity, candidate path/line, concrete trigger, practical
impact and correction. State CODE GO or NO-GO. Do not implement product fixes.
Source hashes must stay stable; no product writer runs during review. Report actual
checks and limitations, then RESULT. Full native source and exact archive gates,
commit/push and release publication remain pending and are owned by the primary.
