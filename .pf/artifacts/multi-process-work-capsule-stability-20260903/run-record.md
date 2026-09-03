# Run Record: multi-process Work Capsule stability

Status: draft

Objective: Stabilize ProcessForge 1.1.0 multi-process project selection and Work Capsule isolation according to the supplied master prompt.

Run: `garage-stabilize-processforge-1-1-0-multi-process-project-selection-and`

Assignment: `stabilize-processforge-1-1-0-multi-process-project-selection-and-work-ca`

Process: `task-batch-execution` 1.0.0, pinned to snapshot `ctx-20260902-065419-56a2ec`.

Scope:

- Add the smallest compatible project-process selection model and pin it to a Work Capsule.
- Keep Garage sessionless and avoid unrelated release/runtime work.
- Add deterministic smoke coverage, schemas, documentation, acceptance evidence, reviews, and a handoff.

Baseline:

- The snapshot is fresh and execution-ready; MCP is unavailable in this host session, so file-first CLI/snapshot access is in use.
- The working tree already has unrelated `.pf` and distribution changes. They are preserved and excluded from this run.
- The current public `pf.work.start` contract accepts only an objective; supporting an optional process choice is in scope.

Planned work items:

1. Audit the current model and write the implementation contract.
2. Implement model, Core/MCP contract, capsule pinning, and compact context behavior.
3. Add schemas, docs, and deterministic smoke/acceptance fixtures.
4. Run focused and release gates; complete independent reviews, validation, and handoff.

Risks:

- Existing uncommitted PF artifacts must not be overwritten.
- This slice must not repair unrelated release-artifact consistency or runtime infrastructure defects.
