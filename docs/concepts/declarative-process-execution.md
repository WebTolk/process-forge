# Declarative Process Execution

ProcessForge executes Process YAML through one universal
`ProcessExecutionService`. Process definitions contain data only. They do not
load Python modules, register callbacks, or provide executable plugins.

The ordinary agent workflow is:

`pf.context -> pf.work.start(objective[, process_id]) -> pf.work.state -> work ->
pf.work.transition(outcome, evidence, notes?) -> pf.work.state -> ... -> run_completed`

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

First write `.pf/artifacts/result.md`, check the blocking tasks and record the
actual results. A transition without the required artifact/gate evidence is
rejected with `transition_rejected` and missing requirements; the stage does
not advance. Inspect `pf.work.state`, satisfy those requirements, then submit
this argument object to `pf.work.transition`:

```json
{
  "project_root": "<project-root>",
  "outcome": "completed",
  "notes": "Task results and blocking-task checks are recorded; ready for run review.",
  "evidence": [
    {"kind": "artifact", "id": "task-result", "path": ".pf/artifacts/result.md"},
    {"kind": "gate", "id": "all-blocking-tasks-completed", "status": "passed", "path": ".pf/artifacts/result.md"}
  ]
}
```

This is an example for these specific obligations, not a universal payload.
Use IDs and allowed outcomes from your actual state. Gate status accepts
`passed`, `approved`, or justified `not_applicable`; `pass` does not satisfy it.
Artifact evidence identifies an existing file; gate evidence is an attestation
of a check actually performed, not independent proof of semantic quality.
Never invent checks or use `not_applicable` merely to bypass a required gate.

The successful response is `stage_transitioned` here. Call `pf.work.state` and
continue through all remaining stages until `action: run_completed`; one
successful intermediate transition does not complete the work.

Each successful transition updates `Assignment.stage`, appends durable stage
history, refreshes the execution projection, and emits `process.stage.*`
events. The final successful transition from the last stage completes the
Assignment and Run automatically and writes the summary and handoff without a
separate terminal completion command.
