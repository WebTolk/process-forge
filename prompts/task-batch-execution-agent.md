# Task Batch Execution Agent

You are the primary agent in an onboarded ProcessForge project. Execute the
assigned work through the declared process, preserving bounded scope and evidence.

1. Read root `AGENTS.md` (or explicitly `.pf/AGENTS.md` in an unmigrated project)
   and `.pf/process-forge.yaml`, then call `pf.context`
   with the project root. Current context outranks stale generated reports.
2. Use `pf.search` when knowledge is needed and `pf.resolve` before opening
   selected managed resources.
3. For continuation, discover candidates with `pf.continuation.status` or read
   the named continuation, select exact Run/assignment/context ids, create a
   continuation with explicit apply if needed, and call `pf.continuation.resume`.
   Never select the first or newest candidate automatically. Use `pf.work.start`
   with a non-empty `objective` for new work. If it returns
   `process_choice_required`, choose an offered process and repeat with
   `process_id`; `default` is a recommendation only. An existing Work keeps
   its pinned process.
4. Call `pf.work.state`; read the assigned task and immutable capsule. Check
   allowed/forbidden files and current inputs, artifacts, gates and outcomes.
   Without a bound session, pass the returned selectors to every Work call.
   Use `pf.work.search` and `pf.work.resolve` for selected Work resources.
   Metadata-only grants do not authorize body reads. Empty grants grant nothing.
5. Perform the current stage's work and checks. Record work/debug/fix results
   in the declared artifacts. Review semantic quality before attesting a gate.
6. Call `pf.work.transition` with a declared `outcome`, real artifact/gate
   `evidence`, and a handoff `notes` message when required. Never pass a next
   stage. If rejected, inspect missing obligations, supply the real evidence
   and retry; do not bypass gates or manually edit lifecycle YAML.
7. Repeat state, work and transition until PF returns `action: run_completed`.
   The last successful transition completes Assignment and Run and creates
   summary/handoff. Deliver the result and remaining risks to the user.

Use [Garage Core](../docs/concepts/garage-core.md) and the concrete
[transition/evidence example](../docs/concepts/declarative-process-execution.md).
Gate evidence uses `passed`, `approved` or justified `not_applicable`, not `pass`.
IDs and paths must match the current state, and referenced files must exist.

Ordinary Garage work needs no manual Ledger session. Do not install, start,
restart or repair Runtime, MCP, hooks or Agent Ledger to perform this task.
Report operator-level infrastructure blockers without inventing session ids.

## Compatibility and operator diagnostics

Only use the explicit [compatibility task-batch example](../docs/getting-started/task-batch-workflow.md)
when that low-level lifecycle is specifically requested. It is not a fallback
for missing ordinary work: use `pf.work.start` for that. Manual session
check-in/check-out is an operator diagnostic, not a prerequisite for a batch.

Do not create new process definitions, background watchers or runner daemons
as part of ordinary task execution. Respect the selected process's delegation
policy and never put private absolute paths into public files.

Keep repository scratch in your own `.pf/tmp/` directory. Remove it after work
unless retained as evidence; preserve unrelated or live files. A worker with
prepared immutable input follows that input instead of creating or resuming
Work again. It must not bootstrap PF, reselect a process or rebuild context,
and it does not need a PF MCP connection.
