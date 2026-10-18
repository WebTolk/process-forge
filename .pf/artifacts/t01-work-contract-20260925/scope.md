# T01 — scope / task record / context / lifecycle

Date: 2026-09-25. Status: ready_for_review. Lifecycle: feature, documentation-only.
Run: garage-t01-pf-vision-alignment-r02-define-the-provider-neutral-work-exec.
Assignment: t01-pf-vision-alignment-r02-define-the-provider-neutral-work-executor-im.
Process: software-feature-development@1.1.0, single_agent; subagents prohibited.
Snapshot: ctx-20260925-140110-0dbc7c; MCP fresh and execution source/installed ready.
Pin: cc411028e9585dd8f56e07faa8997d9e7af1a39a801a0d8c0ca9c8c1e89dfd49.
Source HEAD at intake: a180ad624442d4fbe8ac1710073ef7d4c44babc4.

Operator explicitly authorized AFK sequential implementation of plan r02 after
verification/acceptance of each Work. T08 is completed and accepted; it is not
reopened. This Work defines the common contracts before T09/T02–T06 implementation.

## Allowed writing scope

- .pf/artifacts/t01-work-contract-20260925/** and .pf/logs/t01-work-contract-20260925.md.
- .pf/handoffs/t01-work-contract-20260925.md and .pf/adr/work-execution-contract-20260925.md.
- docs/concepts/work-execution-contract.md (new design contract, implementation status explicit).
- Normal state of this Run/Assignment and generated PF projections.

Read existing plan r01/r02, references, T08 results, source modules, schemas,
tests and documentation. No product Python/schema behavior changes in T01.
Do not edit protected plans, completed T08 evidence, unrelated dirty files,
host configuration, installed Core, Workplace registry or other projects.
No public release/push. Platform: none; no Python toolchain contract exists locally.
No applicable development skill exists in authoritative D:/.agents/skills;
the project-local .pf process is authoritative. Serena/IDE MCP absent, so scoped
UTF-8 source search is the documented fallback. No .agents package in this repo.

## Acceptance

Define Work identity, immutable versioned context and derived stage projection,
authorization/revocation/resource generation, explicit replacement/migration,
scope/actions/outputs/capabilities, transport-neutral executor preparation and
trusted provider adapters. Include logger/journal boundaries, 8 severity levels,
profiles/precedence/locks, retention/privacy and CLI/MCP equivalence from r02.
Every decision needs a positive example, negative case, legacy behavior and
diagnostic expectation. Mark proposed implementation fields distinctly from
existing public API. Base flow must not depend on model identity, MCP or Runtime.

Implementation means delivery of the reviewed contract/ADR/matrix. Review must
be source-backed and primary-only under pinned single_agent policy. Optional
browser/package/public-release work is not applicable; record reasons at gates.
