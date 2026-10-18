# Declarative Process Execution

ProcessForge executes Process YAML through one universal
`ProcessExecutionService`. Process definitions contain data only. They do not
load Python modules, register callbacks, or provide executable plugins.

The ordinary agent workflow is:

`pf.context -> pf.work.start(objective[, process_id]) -> current Work state -> work ->
pf.work.transition(outcome, evidence, notes?) -> returned current state -> ... -> run_completed`

`pf.work.start` selects the declared `initial_stage`, or the first executable
stage when no explicit initial stage exists. It pins the effective Process
definition, version, fingerprint, project context snapshot, and immutable
Assignment capsule. A later edit to Process YAML cannot change the active Run.
If a project authorizes more than one Process, `pf.work.start` can return
`process_choice_required` candidates; the caller must choose one of the offered
process ids. `default` is a recommendation only.

`pf.work.state` exposes only the current execution contract: Process, Run,
Assignment, stage, required inputs, obligations, produced artifacts, entry and
exit gates, allowed outcomes, evidence, and blockers.

`pf.work.transition` accepts an outcome, evidence records, and optional notes.
Linear routing uses the next executable item in `stages[]`. A stage may declare
minimal branching through `outcomes[].next_stage`. The caller never supplies a
next stage, and cross-process `process_transitions` are not used for stage
routing.

Evidence is declarative data. ProcessForge checks deterministic facts such as
presence, repository-relative paths, hashes, gate attestations, required-output
readiness, and verification events. A file path proves existence; it does not
prove that the artifact was semantically reviewed. Agents and humans remain
responsible for semantic quality judgments.

## State, evidence and recovery example

Suppose `pf.work.state` returns this excerpt for `task-result-fixation`:

```json
{
  "stage": {"id": "task-result-fixation", "status": "in_progress"},
  "artifacts": [{"id": "task-result", "kind": "artifact", "satisfied": false}],
  "gates": {"exit": [{"id": "all-blocking-tasks-completed", "required": true, "satisfied": false}]},
  "allowed_outcomes": [{"id": "completed", "next_stage": "run-review"}]
}
```

First write `.pf/artifacts/result.md` within the allowed scope, check the
blocking tasks and record the actual results. Missing required artifact/gate
evidence returns `action: incomplete` with the unsatisfied requirements;
invalid evidence can return `action: transition_rejected`. Neither advances the
stage. Inspect `pf.work.state`, satisfy the requirements, then submit this
argument object to `pf.work.transition`:

```json
{
  "project_root": "<project-root>",
  "run_id": "<returned-run-id>",
  "assignment_id": "<returned-assignment-id>",
  "context_id": "<returned-context-id>",
  "outcome": "completed",
  "notes": "Task results and blocking-task checks are recorded; ready for run review.",
  "evidence": [
    {"kind": "artifact", "id": "task-result", "path": ".pf/artifacts/result.md"},
    {"kind": "gate", "id": "all-blocking-tasks-completed", "status": "passed", "path": ".pf/artifacts/result.md"}
  ]
}
```

This is an example for these specific obligations, not a universal payload.
Use IDs and allowed outcomes from your actual state. Keep the exact selectors
returned by start/resume; without a bound session, supply them on every Work
call. Check the Assignment and capsule permissions before writing an artifact.
For an existing Work, use [continuation](work-continuation.md) rather than
rewording the objective in another start call. Gate status accepts
`passed`, `approved`, or justified `not_applicable`; `pass` does not satisfy it.
Artifact evidence identifies an existing file; gate evidence is an attestation
of a check actually performed, not independent proof of semantic quality.
Never invent checks or use `not_applicable` merely to bypass a required gate.

The successful response is `stage_transitioned` here. When the response includes
the complete current Work projection, use it for the next action. Call
`pf.work.state` when that projection is absent or after uncertainty, reconnect,
or concurrent changes; a second identical read is not required after every
successful transition. Continue until `action: run_completed`; an intermediate
transition does not complete the work.

Each successful transition updates `Assignment.stage`, appends durable stage
history, refreshes the execution projection, and emits `process.stage.*`
events. The final successful transition from the last stage completes the
Assignment and Run automatically and writes the summary and handoff without a
separate terminal completion command.

Manual batch record commands such as `run-create` and `task-complete` serve a
separate [advanced workflow](../getting-started/task-batch-workflow.md). Do not
add `run-complete` or `run-summary` to close this governed Work: the final
transition owns completion. Host session lifecycle remains separate.

## Internal iterations and nested work

A Run can contain repeated investigation, domain/architecture reasoning, approved
revisions, implementation and focused checks for one cohesive result. This does
not imply a transition after every edit or final acceptance/publication for every
iteration. Use only the actions and outcomes allowed by the current contract;
this guidance adds no backward route or edit permission. See
[Run boundaries and iterations](process-definition-run-task-iteration.md#choosing-a-run-boundary).

A substantial worker package may use its own complete process nested within the
parent cycle. Its output is reviewed and integrated by the primary; child
completion does not finish or publish the parent automatically.

## Executor results and continuation

A worker can consume [prepared input](prepared-input.md) without an MCP
connection. Its result collection preserves the primary governed Run,
Assignment stage and immutable capsule; the primary agent still reviews
the result and supplies stage evidence. Legacy task collection has a separate
compatibility completion path. Receipt recovery and repeated collection must
not duplicate completion events in either path.

Changing executor preferences or reconnecting does not authorize a new intent,
snapshot or resource set. Check the durable Work identity, current stage and
accepted evidence after reconnect. Stage obligations come from the pinned
process and current assignment; they do not require rewriting the capsule.
See [Work context](work-context.md) and [Work resources](work-resources.md).
