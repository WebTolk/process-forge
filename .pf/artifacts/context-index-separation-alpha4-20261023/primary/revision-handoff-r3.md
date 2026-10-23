# Governed handoff to the clarified alpha4 implementation

Preserve R1 architecture, all capsules and failed attempts. The user clarified
manual CLI/common component, future scheduling and storage/backend extension.
architecture-r2.md, storage-decision-r3.md and trigger-policy-r4.md are the current
design inputs. Initial Codex launches returned HTTP403; the ordinary observation
retry recovered model access and emitted real READ_ACK/implementation messages in
its managed usage receipt. Empty stdout/starting heartbeat were not proof of a
stalled model: codex_exec_worker writes progress into usage-attempt-N/codex.jsonl.
Primary stopped attempt2 too early; its partial work is retained and attempt3
continues the unchanged observation remit. No accepted result yet.

Primary integration and maintenance/scheduler contributor scopes now need governed
successors pinning the clarified revisions. Cancel their old reservations through
native Work lifecycle; do not edit capsules. Reuse the exact primary write scope.
Maintenance successor also owns existing search_index.py adapters so all explicit
mutating CLI commands call one indexing component with their preserved scope and
format. It may define a narrow real backend Protocol in index_maintenance.py or
index_backend.py; reuse ResourceSearchIndex, not a duplicate engine or second DAL.
The common workplace service .run remains callable by new manual CLI and a cold
future-scheduler job. Existing project-scoped commands retain current parameters
and error/status/output mapping and cannot obtain workplace-wide indexing grants.

Scheduler successor owns only resources/index_schedule.py and its tests: a cold
explicit callable that invokes the same component. It does not edit Runtime,
spawn threads, configure timers or claim periodic scheduling delivered. Four
logical contributors remain observation, maintenance, future job contract and
deferred integration/docs. One native reviewer starts after all implementation.

Native monitoring must read actual managed usage receipts and owned file/report
timestamps; do not infer absence of execution from wrapper stdout alone. Forward
real READ_ACK/RESULT messages to PF chat with attribution. Preserve prior HTTP403
receipts and do not claim service/credential repair or bypass. No live indexing,
device update or infrastructure lifecycle is authorized.
