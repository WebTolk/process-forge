# Native PF worker brief: R02 storage foundation

Read plan.md beside this file and your role brief. You are one of four native
PF shell workers in operator-authorized 1-1-4; the primary is ONLY orchestrator.
Use gpt-6.1-sol, reasoning high. No nested workers. This first contribution is
analysis/design only; write your report, implementation-map.json and log under
your own artifact directory, scratch only in your own .pf/tmp subdirectory.
Do not modify product, old accepted artifacts, assignment/capsule, infrastructure,
live databases, project manifest, main Git HEAD/index or other dirty files.

Read .pf/AGENTS.md, pf.context, exact Work state and immutable capsule. Use only
the exact selectors from your launch; no newest/default task selection. Resolve
PF knowledge/resources with work.resolve before opening. Use Serena first for
code navigation, falling back to bounded shell if unavailable. Load selected
Python knowledge and existing architectural documents needed by the role.
Do not scan huge runtime/history directories or entire archived source copies.

The latest operator instruction authorizes development of the proposed R02
block, preserving all released external contracts and familiar agent workflows.
Historical backlog `implementation_authorized=false` describes registration,
not a rejection of this latest instruction. This analysis Work itself remains
artifact-only. Implementation requires the next scoped Work and frozen design.

Keep KISS: one workplace SQL DB, one SQL DB in each project .pf, separate search
index DB. Project task canonical state lives in project; workplace summaries
and references are projections. Own PF SQL API/classes reusable by Core and
processes, first SQLite driver; future RAG/search backend separate from accounting.
No generic agent scheduler, ORM framework, plugin/container framework, all-SQL
backend implementation or speculative compatibility layers.

Read latest storage requirements, original spec, roadmap and Python quality
context pinned to your Work. Verify current source owner paths. Report what
exists vs proposed; exact files/symbols, risks and regression checks. Reference
existing migration/update/SQLite helpers instead of inventing parallel systems.
Include an exact suggested implementation ownership list to avoid overlapping
writers, APIs needed from others and evidence that old CLI/MCP/file-only work.
Use Russian reports with portable paths. Do not expose secrets or private paths.

PF coordination: use native agent-checkin/agent-heartbeat for YOUR registered
identity and session. Read the task handoff recorded in your own PF session,
append READ_ACK using chat-record as yourself (not on behalf of another agent),
and append RESULT_READY with report paths and limitations at completion.
Capture alone is not read acknowledgement. Discover CLI flags through --help.
Do not restart Ledger if unavailable. Keep heartbeat during long work.

Lifecycle: this is a bounded contribution to a parent cohesive result. Do not
prematurely mark parent/implementation/review done. Record truthful evidence
for your current native stage; if native worker collection completes this
contribution, leave parent transitions to orchestrator. Native worker reports
must satisfy the actual requested worker-report protocol as well as your
Markdown report. Do not make commits/push from this first research wave:
delivery is serialized by the primary after all four reports are reconciled;
a designated native worker performs candidate/commit work later.
