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
Artifact evidence may identify an existing file; gate evidence is an attestation
of a check actually performed, not independent proof of semantic quality.
Never invent checks or use `not_applicable` merely to bypass a required gate.

## Evidence guidance

The shared CLI/MCP Work projection includes additive `evidence_guidance`.
For active Work with valid pinned context and ready permissions it lists
unsatisfied requirements, exact accepted kinds, ID keys and statuses, examples,
and explanations of existing diagnostics. Its `transition_template` preserves
the returned selectors. Replace placeholders and supply truthful evidence only
after doing the work. With multiple outcomes, choose an offered outcome yourself.
Terminal, invalid or blocked Work receives no actionable template.

The following IDs are illustrative; use the IDs from your own response:

| Requirement | Positive record | Negative record and reason |
| --- | --- | --- |
| Artifact `change` | `{"kind":"artifact","artifact_id":"change","status":"ready"}` | `{"kind":"gate","id":"change","status":"approved"}` has the wrong kind. |
| Input `brief` | `{"kind":"input","input_id":"brief","status":"present"}` | `{"kind":"input","id":"brief-typo","status":"ready"}` has the wrong ID. |
| Evidence `review` | `{"kind":"attestation","evidence_id":"review","status":"ready"}` | `{"kind":"attestation","artifact_id":"review","status":"ready"}` uses the wrong ID field. |
| Gate `build-ready` | `{"kind":"gate","gate_id":"build-ready","status":"approved"}` | `{"kind":"gate","id":"build-ready","status":"pass"}` has an unacceptable status. |
| Justified exception | `{"kind":"gate","gate_id":"optional-check","status":"not_applicable","reason":"No UI changed","evidence":["reviewed-diff"]}` | The same record without a reason or with an empty supporting `evidence` list is rejected. |

Artifact, input and required-evidence statuses accept `ready`, `present`,
`passed`, `approved`, and justified `not_applicable`. Gates accept only `passed`,
`approved`, and justified `not_applicable`. Artifact IDs use `artifact_id` or
`id`; inputs also accept artifact records and `input_id`, `artifact_id` or
`id`; required evidence accepts kinds `attestation`/`evidence` and `evidence_id`
or `id`. Gate matching uses a nonempty `gate_id` before its fallback `id`.
The latest matching record controls readiness, including a later failing record.
Inputs/entry gates use accumulated evidence; outputs/exit gates use current-stage
evidence. A saved supplemental or mismatched record may remain in evidence without
satisfying a requirement; `unmatched_evidence` is advisory, not a new rejection.

`conditional_next_entry_gates` comes from the pinned process and each offered
outcome. These gates may already be satisfied by accumulated evidence; guidance
does not evaluate them or select a route. If a transition reports
`entry_gate_evidence_missing`, use the corresponding conditional example.
Required handoff text belongs in `transition.notes`.

A file `path` is optional under the existing evidence contract. If supplied,
it must identify an existing regular file within the authorized project root;
`missing.md`, `../outside.md`, a directory, or an absolute path is invalid.
PF computes the digest from that file, replacing any caller-supplied `sha256`.
A missing saved digest or a file changed since submission leaves the requirement
unsatisfied. Review and resubmit the actual file; a hint never repairs or accepts
it. Normalization failures retain their existing blocker codes and add
`evidence_guidance.request_errors` explanations with evidence indexes.

Guidance performs no file access, grants no scope, and changes no evidence or
transition decisions. All examples use the same matcher vocabulary as readiness.

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
