# Process Authoring

Process id: `process-authoring`

This built-in process describes how ProcessForge creates new process packs from
guided answers, reviews the generated draft, applies public files, and validates
the result with `process-doctor`.

## Stages

- `intake`: capture process identity, scope, roles, stages, artifacts, gates, and run model.
- `draft-process`: generate a schema-compatible process candidate.
- `logic-review`: check duplicate ids, missing references, handoff order, and task-loop consistency.
- `apply-process`: write the process, prompt, documentation, and example files.
- `process-doctor`: validate the applied process pack.
- `handoff`: record delivered state and residual risks.

## Public Outputs

- `processes/<process-id>.yaml`
- `prompts/<process-id>-agent.md`
- `docs/processes/<process-id>.md`
- `examples/process-authoring/<process-id>/`
