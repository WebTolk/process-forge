# Multi-process project current-state audit

Status: ready_for_review

## Baseline

- Project context snapshot `ctx-20260902-065419-56a2ec` is fresh and execution-ready.
- The effective coordination mode is `simple`; no Runtime, Ledger, hook, or external session is required for Garage work.
- Existing unrelated uncommitted `.pf` and `dist` files predate this run and are excluded.

## Current implementation facts

| Surface | Current behaviour | Gap for this slice |
| --- | --- | --- |
| Manifest | The schema has a catalog-like `processes` array; normal work selection reads the legacy singular `process` and falls back to `task-batch-execution`. | No default-plus-allowed project selection contract. |
| `pf.context` | `garage.process_summary()` exposes only `snapshot.processes.current` id and stage count. | It cannot expose a compact allowed-process catalog. |
| `pf.work.start` | Core, CLI and MCP accept only `objective`; Core resolves one singular selected process. | No explicit `process_id`, rejection, or ambiguous-choice response. |
| Run and Assignment | One `process`, process-definition fingerprint and snapshot are pinned; specializations are currently empty. | Active specializations and selected-resource identities are not explicit per Work. |
| Assignment capsule | Pins snapshot and process definition but has an empty specialization/resource context. | It needs an active Work capsule, not a union of the snapshot. |
| Process catalog | Resolver already resolves only one named definition and can provide process metadata. | It needs a compact candidate adapter; no second resolver is needed. |
| Process transitions | Routes/handoffs already exist as a distinct model. | Completion does not produce compact next-work advisory data. |

## Constraints confirmed

- Keep legacy `process: <id>` working without a migration.
- Do not create a session manager, Runtime prerequisite, classifier, or second resolver.
- Keep a process transition separate from a stage transition: the target work gets a new Run, Assignment, and immutable capsule.
- Treat active Work pins as authority after start; later manifest/snapshot edits cannot mutate them.

## Source and reference surfaces read

`src/processforge_core/garage.py`, `src/processforge_core/process_execution.py`, `src/processforge_core/process_catalog/service.py`, `tools/pf_runtime/mcp_server.py`, `tools/processforge.py`, the listed schemas, templates, and concept documents on Garage, capsules, transitions, and specializations.

## Decision

Extend the existing singular selection path with a small normalizer and extend its existing pinned run/capsule payload. The canonical project-level source remains the manifest; the snapshot carries only compact resolved selection metadata.
