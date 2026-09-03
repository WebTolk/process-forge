# Baseline audit: Ledger, Runtime, Codex hooks, and MCP

- Date: `2026-08-14`
- Assignment: `ledger-hooks-mcp-next-stage-20260814`
- PF context: `ctx-20260814-035156-d5d5ac` (`fresh`, policy action `continue`)

## Architectural decision

PF Core remains the sole owner of Agent Ledger, Project Router, events, Agent
Director, Execution Inspector, resource resolution, and projections. PF Runtime
remains a workplace-scoped lifecycle, scheduler, IPC, and adapter-ingress layer.
The Codex adapter and MCP server are thin interfaces and never create a second
session/project model.

## Live-state inventory

| Data | Current location | Classification | Required direction |
| --- | --- | --- | --- |
| Agent, session, project, process/run/task, presence and heartbeat | workplace Agent Ledger and presence records | authoritative | Use for every session-to-project decision. |
| Process events | project `.pf/runtime/events/events.ndjson` | authoritative facts | Continue to append through existing PF Core. |
| Runtime service identity, lock, endpoint, token and scheduler timestamps | workplace `runtime/pf-runtime/` | transport-only | Preserve daemon-lifecycle contract. |
| Runtime project handles | workplace `runtime/pf-runtime-host/state.json` | derived cache | Rebuild from Ledger/project state where needed. |
| Runtime `sessions` map | workplace `runtime/pf-runtime-host/state.json` | duplicate cache currently used as authority | Rebuild from Ledger; never route from it. |

## Confirmed documentation-to-code mismatch

`tools/pf_runtime/host.py` documents its session map as a rebuildable cache, but
`project_for_session()` first routes through that map and uses Ledger presence
only to obtain a project id that is then resolved through cached project handles.
The `/session/register` IPC endpoint writes only that cache and does not produce a
Ledger check-in. This conflicts with the requested canonical Ledger binding and
prevents recovery after deletion of the Runtime cache.

## Existing capabilities retained

- `host.ingest_event()` already prevents a known session from submitting an event
  to another project.
- `ledger_from_event()` already delegates check-in, heartbeat and checkout to PF
  Core commands.
- Runtime daemon lifecycle is protected by `instance_id`, singleton ownership,
  ready checks and orphaned-instance handling; this assignment must not weaken it.
- `command-history` is already a deterministic projection from the event journal,
  so it is the selected single projector.

## Baseline limits

- No active Codex lifecycle-hook binding is present in the user configuration.
- There is no executable stdio MCP facade yet; existing Runtime read commands are
  MCP-like but not an MCP server.
- `runtime resolve` currently resolves only a routed project handle, not a named
  resource from the resolved PF context.

## Scope boundary

Platform classification and capability-resolution issues are outside this
assignment. Existing dirty worktree changes are user-owned and are preserved.
