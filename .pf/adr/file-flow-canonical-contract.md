# ADR: File Flow Canonical Contract

- date: `2026-07-25`
- status: accepted
- source audit: `.pf/artifacts/file-flow-audit-report.md`
- implementation plan: `.pf/artifacts/file-flow-fix-plan.md`

## Decision

ProcessForge uses one canonical owner for each durable file-flow fact:

- run state: `.pf/runs/<run>/run.yaml`
- task state: `.pf/assignments/<task>.yaml`
- public deliverables: `.pf/artifacts/**`
- public reviews: `.pf/reviews/**`
- public handoffs: `.pf/handoffs/**`
- public logs: `.pf/logs/**`
- private runtime observations: `.pf/runtime/**`

Executable task statuses are limited to:

- `open`
- `in_progress`
- `blocked`
- `debugging`
- `review`
- `done`
- `cancelled`
- `failed`

Run statuses are limited to:

- `draft`
- `open`
- `in_progress`
- `blocked`
- `review`
- `completed`
- `cancelled`
- `failed`

Assignment capsules are the canonical worker launch descriptors for the active `worker-run` path. New capsules record the assignment checksum and are treated as immutable for automated worker launches. If an assignment changes after capsule creation, `worker-run prepare/start` must reject the stale capsule instead of silently overwriting it.

Execution Context Packages remain a compatibility/legacy context artifact for `context-compile`; they are not required by the active `assignment-capsule` and `worker-run` path.

## Consequences

- JSON Schema, doctor commands, and mutating CLI commands must enforce the same executable run/task lifecycle.
- `task-complete` must not mark a task `done` unless required outputs exist or a durable waiver is recorded.
- `run-complete` must leave a completed run with summary and handoff artifacts.
- Default durable doctor checks must not depend on private `.pf/runtime/**` logs.
- Runtime driver manifests must not override ProcessForge-owned `PF_*` worker identity variables.
- `.pf/runs/<run>/artifacts` and `.pf/runs/<run>/reviews` are deprecated; new runs should not create them.

## Rationale

Autonomous multi-agent work needs stable evidence. A worker report is only trustworthy when the assignment, capsule, required outputs, and completion status all describe the same durable contract. Silent capsule overwrites, private runtime dependencies, and schema/doctor drift make agent work non-reproducible.

This decision keeps the active implementation small: it hardens the current capsule-based worker path instead of reviving ECP as a mandatory launch package.
