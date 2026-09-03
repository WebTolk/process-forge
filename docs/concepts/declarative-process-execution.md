# Declarative Process Execution

ProcessForge executes Process YAML through one universal
`ProcessExecutionService`. Process definitions contain data only. They do not
load Python modules, register callbacks, or provide executable plugins.

The ordinary agent workflow is:

`pf.context -> pf.work.start(objective) -> pf.work.state -> work ->
pf.work.transition(outcome, evidence) -> pf.work.state`

`pf.work.start` selects the declared `initial_stage`, or the first executable
stage when no explicit initial stage exists. It pins the effective Process
definition, version, fingerprint, project context snapshot, and immutable
Assignment capsule. A later edit to Process YAML cannot change the active Run.

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
readiness, and verification events. Agents and humans remain responsible for
semantic quality judgments.

Each transition updates `Assignment.stage`, appends durable stage history,
refreshes the execution projection, and emits `process.stage.*` events. A
successful transition from the final stage completes the Assignment and Run
and writes the summary and handoff automatically.
