# PF Runtime Director Ledger PoC Report

- date: 2026-08-13
- run: `pf-runtime-director-ledger-20260813`
- assignment: `runtime-director-ledger-poc-20260813`
- status: implemented

## Implemented Slice

Added a lazy Runtime host PoC:

- `runtime-host init`: records rebuildable project handles in workplace runtime state.
- `runtime-host event`: accepts normalized adapter JSON, routes it to the correct project, appends an existing ProcessForge event envelope, updates Agent Ledger for session lifecycle events, and rebuilds a command-history projection.
- `runtime-host project-state`, `work-state`, `resolve`: read-only MCP-like surfaces bound by session-to-project routing.
- `runtime-host tick`: hosts existing Ledger stale detection plus existing `agent-director-tick` for organized projects and existing execution-inspector/supervisor tick for selected projects.
- `runtime-host rebuild-projections`: rebuilds projections from durable event journals after a simulated restart.

New files:

- `tools/pf_runtime/__init__.py`
- `tools/pf_runtime/host.py`
- `schemas/pf-runtime-agent-event.schema.json`
- `tools/smoke_runtime_host_poc.py`

Updated file:

- `tools/processforge.py`

## Boundary Kept

The PoC does not add a second Director, Inspector, Ledger, context resolver, or writer layer.

- Events are written through `append_process_event`.
- Agent presence is updated through existing Agent Ledger functions.
- Director scheduling is delegated to existing `command_agent_director_tick`.
- Execution observation is delegated to existing `command_supervisor_tick`.
- Project mode is resolved through existing `effective_project_coordination`.
- Runtime state stores only cache/handles/sessions under workplace runtime.

## Proof

`tools/smoke_runtime_host_poc.py` proves:

- one runtime host tracks two onboarded PF projects;
- Project A and Project B events land in separate `.pf/runtime/events/events.ndjson` files;
- session-routed `project-state` returns the correct project for `sess-a` and `sess-b`;
- Agent Ledger sees runtime-created session presence;
- organized projects get a hosted Director tick;
- simple projects are skipped by Director hosting;
- Inspector tick is hosted through the existing supervisor implementation;
- projection rebuild works after simulated restart;
- project `events-validate` still passes.

Focused checks run:

- `python -m py_compile tools/processforge.py tools/pf_runtime/__init__.py tools/pf_runtime/host.py tools/smoke_runtime_host_poc.py`
- `python tools/smoke_runtime_host_poc.py`
- `python tools/smoke_agent_ledger.py`
- `python tools/smoke_agent_director_tick.py`
- `python tools/smoke_process_supervisor_tick.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/processforge.py events-validate --project-root .`

## Remaining Limit

`python tools/validate-process-forge-checksums.py --root . --check` is still failing. The inventory was already stale across several release files, and this slice adds new public files plus a `tools/processforge.py` change. The inventory was not rewritten in this task to avoid folding unrelated release-state drift into the runtime PoC.

## Not Implemented

- no Windows Service or always-on daemon;
- no loopback HTTP server;
- no network sync adapter;
- no write MCP tools beyond event ingestion;
- no command execution from hook payloads;
- no new Director/Inspector decision semantics.
