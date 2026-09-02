# <Process Name> Agent

Process id: `<process-id>`

Use the high-level ProcessForge workflow:

`pf.context -> pf.work.start(objective) -> pf.work.state -> work ->
pf.work.transition(outcome, evidence) -> pf.work.state`

Rules:

- Let ProcessForge select stages from the pinned Process definition.
- Record durable evidence for every blocking gate and produced artifact.
- Provide an outcome and evidence; never provide `next_stage`.
- Run review before handoff when the process defines a review stage.
- Keep public files portable and free of secrets.
- Continue until ProcessForge returns `action: run_completed`.
