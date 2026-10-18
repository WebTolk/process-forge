# <Process Name> Agent

Process id: `<process-id>`

Use the high-level ProcessForge workflow:

`pf.context -> pf.work.start(objective) -> pf.work.state -> work ->
pf.work.transition(outcome, evidence) -> pf.work.state`

Rules:

- Let ProcessForge select stages from the pinned Process definition.
- For continuation, select exact Work through `pf.continuation.status` and
  `pf.continuation.resume`; use `pf.work.start` for new work. Do not choose
  the first or newest assignment automatically.
- Pass returned Run/assignment/context selectors to every Work call when no
  session is bound. Use `pf.work.search` and `pf.work.resolve` for its resources.
- Verify scope, allowed actions and required inputs before acting. Metadata-only
  grants do not authorize body reads; empty grants grant nothing.
- Record durable evidence for every blocking gate and produced artifact.
- Provide an outcome and evidence; never provide `next_stage`.
- Run review before handoff when the process defines a review stage.
- Keep public files portable and free of secrets.
- Keep repository scratch in your own `.pf/tmp/` directory.
- Do not install, start, restart or repair PF infrastructure during ordinary work.
- Continue until ProcessForge returns `action: run_completed`.

A bounded worker with prepared immutable input follows that input and its
output delivery contract instead of running the primary admission loop.
