# Python Core Structure

The core is evolving incrementally. `tools/processforge.py` is still the active legacy facade, not retired code. Existing CLI, MCP, hook entrypoints and bootstrap aliases remain unchanged.

## Current Ownership

| Module | Responsibility |
| --- | --- |
| `src/processforge_core/garage.py` | Project/context/read-model services, including `CurrentWorkService`. |
| `src/processforge_core/process_execution.py`, `continuation.py` | Governed lifecycle, selection, pinned execution, evidence and completion/recovery. |
| `src/processforge_core/document_store.py`, `work_inventory.py` | YAML reading and live sorted discovery; no shared mutable document cache. |
| `src/processforge_core/ports.py` | Internal structural dependencies; the first port has only flow-root resolution and document reading. |
| `src/processforge_core/composition.py` | Explicit current-work service factory and a two-operation adapter for the legacy module. |
| `src/processforge_core/bootstrap.py` | Existing runtime module assembly and lazy access to the current-work factory. |
| `tools/processforge.py`, `tools/pf_runtime/` | Legacy CLI facade and transport/host/provider adapters. |

`build_current_work_service(project_root, port)` accepts any structurally compatible read dependency and constructs the existing service without importing the CLI or doing I/O. `RuntimeBootstrap.current_work_service(project_root)` uses the already-loaded legacy core through `LegacyWorkReadAdapter`. No service locator, global service cache or DI container is introduced.

The existing `CurrentWorkService(project_root, core)` constructor and module path are preserved. Its discovery order, missing-assignment fallback, bootstrap-placeholder handling, summary shape and error behavior are unchanged. Existing consumers need not migrate immediately.

## Boundaries

Ports and composition are internal, provisional interfaces, not additions to the package's stable public API. A `Protocol` describes dependencies for type checking; it does not authorize filesystem access or validate grants. The current-work port has no transition or write methods.

Other services still depend on the legacy core. The target separation is domain decisions, application services, infrastructure adapters and thin transports, assembled explicitly. Those layers are not fully extracted yet. Historical formats, pinned capsules, protective refusals and trusted provider boundaries must survive subsequent changes.

`tools/smoke_core_read_composition.py` checks characterization, fake-port composition, bootstrap fields, delegation and an isolated installed-shaped package without a CLI. That fixture is not acceptance of an actual installed Core or connected host. Source, archive, installed and connected-host qualification remain distinct.
