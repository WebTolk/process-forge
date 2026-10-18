# Orchestration

Objective: architecture only for a shared Work metadata projection, storage and freshness. No product code, tests, installation or infrastructure changes are authorized.

Current project context: ctx-20261016-091113-310bed, fresh, policy_action continue. Exact Work identity and immutable capsule were read and validated; execution_readiness ready, planning_only, read/write_artifact only, subagents forbidden. Writable outputs are limited to this artifact directory and the named handoff. Required diagnostic inputs are immutable and readable. No platform/toolchain overlay is fixed by the selected context.

Plan: scope -> inspect current readers, completion and writers -> model common facts and separate policies -> decide RAM/storage/freshness/concurrency -> review scenarios -> deliver a design and implementation plan only. One primary architect; no delegation. Runtime and MCP remain as connected. Required output: architecture.md. Existing unrelated dirty files and public CLI/MCP contracts are preserved.

Task record, execution-context-summary and lifecycle-mode-decision are contained here. context-ready: passed against live PF state and read capsule.
