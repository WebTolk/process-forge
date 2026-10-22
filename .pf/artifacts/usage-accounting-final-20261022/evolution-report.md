# Experience and follow-up boundaries

2026-10-22, primary orchestrator. The implementation cycle used native PF shell
workers on gpt-6.1-sol: high effort for source qualification, Core/integration and
first independent review; medium for the bounded two-finding re-review. Product
writers had disjoint scopes and explicit handoffs. Primary performed final bounded
integration, registered QA and acceptance. Every accepted participant recorded
actual PF Python/OOP material reads, not only resource discovery.

Knowledge provenance: PF supplied the authoritative domain/architecture, Python
dataclasses/typing, style/docstring guidance and current scope/capsules. Direct
source/receipt inspection supplied provider schemas and observed usage. Agent
knowledge supplied implementation reasoning, which was checked against those
materials and executable tests. Primary device memory helped navigate native
worker/Ledger workflow; it did not replace live PF context or source evidence.

Independent review found two issues that the initial 65 tests missed: malformed
timestamp runtime validation and I/O between paired clock observations. Both were
reproduced before correction and protected by regressions; the revised suite has
68 tests and 36 subtests. Keep independent behavioral review as a separate gate.

PF workflow follow-ups observed, outside this feature's product scope:

- Work-start scope declarations do not currently express the prepared worker's
  workspace knowledge grants; a valid Work can therefore prepare no usable Python
  material. Required grants should be explicit before worker launch.
- Legacy task-create inside a process-pinned Work run does not inherit a compatible
  task process pin. This cycle used a separate native worker run rather than
  editing pinned state or widening a capsule.
- Registry QA commands lack a path_ref accepted by worker preparation. Primary
  ran the registered launcher; no registry repair or tool installation was made.
- An unbound worker MCP session may fail while exact native CLI Ledger/chat works.
  Pre-registration plus the explicit session avoided that ambiguity for reviewers.

Data qualification limits remain explicit: modern Kimi has a source-qualified
projection/import profile and synthetic coverage, not automatic native capture.
Earlier attempts before the driver change have unknown usage. The first core-fix
receipt is prototype evidence predating counter/clock normalization amendments;
its immutable history was not silently rewritten. Later review attempts qualify
actual capture and idempotent replay. Observation freshness may advance on replay;
facts, counts, durations and totals must not.

Future Control Center/TUI, Codex plugin and optional REST should use the shared
application service and explicit authorized project sets. Stable origin/source/
record identities and immutable revisions support later transport. No speculative
UI, synchronization protocol, money or pricing layer was added.

Worker test leftovers whose removal was rejected remain excluded from delivery;
no permissions/ACL workaround was attempted. Raw receipts and private preparation
inputs remain local. No new task, release or device restart follows this cycle.
