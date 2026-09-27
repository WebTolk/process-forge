# Repository Map

Reviewed on 2026-09-27. This is a maintained responsibility map, not a recursive
listing of historical temporary files. Paths below are relative to the repo.

## Runtime implementation

| Path | Responsibility |
| --- | --- |
| `bin/pf.py` | Public CLI launcher |
| `tools/processforge.py` | Command registration and orchestration |
| `src/processforge_core/bootstrap.py` | Core bootstrap |
| `src/processforge_core/garage.py` | File-first Garage operations |
| `src/processforge_core/process_execution.py` | Pinned process execution and transitions |
| `src/processforge_core/work_context.py` | Work execution contexts/contracts |
| `src/processforge_core/work_resources.py` | Work resource authorization |
| `src/processforge_core/work_resource_material.py` | Bounded authorized material |
| `src/processforge_core/prepared_input.py` | Prepared immutable executor input |
| `src/processforge_core/egress/` | Policy, classification, views, storage, broker and transport |
| `src/processforge_core/core_update.py` | Manifest-controlled Core updates |
| `src/processforge_core/diagnostics.py` | Optional diagnostics |
| `src/processforge_core/runtime_metrics.py` | Bounded local activity metrics |
| `src/processforge_core/host_integration.py` | Host integration boundary |
| `src/processforge_core/local_resource_search.py` | Local resource search |
| `src/processforge_core/process_catalog/` | Process catalog |
| `src/processforge_core/common/` | Shared Core helpers |

## Product data and validation

| Path | Responsibility |
| --- | --- |
| `packs/official/` | Bundled domain processes and packages |
| `processes/` | Core/custom process definitions and companions |
| `packages/` | Knowledge/package manifests |
| `schemas/` | JSON Schema contracts |
| `templates/` | Assignment, artifact, review, handoff and other templates |
| `docs/`, `docs/ru/` | English/Russian documentation |
| `prompts/`, `examples/`, `seeds/` | Agent entry points and reusable examples |
| `tools/smoke_*.py` | Behavioral smoke/regression checks |
| `tools/validate-*.py` | Schemas, checksums and public-cleanliness checks |
| `checksums/` | Public checksum inventory |
| `dist/`, `updates/` | Distribution/update artifacts and metadata |

## Project-local process state

`.pf/AGENTS.md` and `.pf/process-forge.yaml` are the entry points. Assignments and
runs live under `.pf/assignments/` and `.pf/runs/`. Immutable assignment capsules
live under `.pf/contexts/assignment-capsules/`. Artifacts, reviews, ADRs, logs and
handoffs have separate directories. `.pf/runtime/` contains derived operational
state. Temporary work belongs under `.pf/tmp/`; declared durable evidence there
is retained. No project-local `.agents` flow package was present at this review.

Current navigation: [artifact index](README.md),
[coverage matrix](artifact-completion-20260927/coverage.md),
[egress design](../../docs/concepts/egress-engine.md),
[Work context](../../docs/concepts/work-context.md),
[Runtime monitor](../../docs/concepts/runtime-monitor.md).
