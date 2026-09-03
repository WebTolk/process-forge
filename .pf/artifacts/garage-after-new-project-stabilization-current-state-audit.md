# Current State Audit: Garage Stabilization After New Project Test

Generated: 2026-08-24 12:00 +04
Run: `garage-stabilization-after-new-project-20260824`
Assignment: `garage-after-new-project-baseline-20260824`

## Executive Summary

The current checkout is materially better than the original Garage baseline after
the previous stabilization slice: project-local Codex hooks are installed, the
project context is fresh, deterministic initialization artifacts are present,
and the search-index status command reports SQLite FTS5 availability.

The remaining gaps are not cosmetic. The real fresh Codex SessionStart path is
still not proven in this already-running Codex session, MCP remains unconfigured
in the current project resource profile, the local search index is fresh but has
zero indexed resources/documents for this project snapshot, and Runtime status
still exposes historical stopped metadata with old runtime version labels.

## Commands And Evidence

- `python tools/processforge.py project-context-check --project-root .`
  - `SNAPSHOT_ID: ctx-20260824-083958-50e142`
  - `STATUS: fresh`
  - `RESOURCE_READINESS: fresh`
  - `EXECUTION_READINESS: ready`
- `python tools/processforge.py project-init-status --project-root . --workplace D:\.agents\processforge-workplace --json`
  - `state: complete`
  - `snapshot.status: fresh`
  - `snapshot_health: warn`
  - `workplace: reachable`
  - `mcp: not_configured`
  - `codex_integration.status: installed`
  - `codex_integration.scope: project-local`
  - `codex_integration.target: .codex/hooks.json`
- `python tools/processforge.py search-index status --project-root . --workplace D:\.agents\processforge-workplace`
  - `STATUS: fresh`
  - `SQLITE_VERSION: 3.50.4`
  - `FTS5: available`
  - `RESOURCES: 0`
  - `DOCUMENTS: 0`
- `python tools/processforge.py runtime status --workplace D:\.agents\processforge-workplace --json`
  - `status: stopped`
  - `health: stopped`
  - `runtime_version: 1.0.0-poc`
  - `processforge_core_version: 1.0.2`
  - historical endpoint/PID metadata is still present in the status payload.

## Confirmed Gaps

1. Fresh Codex bootstrap is installed but not live-proven. Existing hooks config
   is visible, but a real Codex SessionStart emitted by a newly opened session
   cannot be generated from inside this already-running worker.
2. MCP capability is not configured for the current project profile. This keeps
   the Garage "Codex opens project -> MCP tools ready" path partial.
3. Search index freshness is not the same as content readiness. The index is
   fresh and FTS5-capable, but the current snapshot contributes no indexable
   resources/documents.
4. Missing-session MCP diagnostics are too terse in the current implementation:
   `safe_tool_error()` returns only `{"error":{"code":"missing_session"}}`.
5. Current-session projection is updated on check-in, heartbeat and checkout.
   The stale-presence updater marks Ledger presence stale and emits
   `agent.session_expired`, but the observed code path does not rewrite the
   project-local current-session projection after expiry.
6. Runtime status reports protocol/core version fields, but stopped historical
   service metadata can still look like an active endpoint/PID record unless the
   consumer interprets `status`/`health` correctly.

## Baseline Decision

Proceed with a narrow implementation slice:

- enrich MCP missing-session diagnostics;
- expose the previous hook repair action through MCP schema;
- keep stale current-session projection synchronized with Ledger expiry;
- add focused smokes for the two confirmed behavioral gaps and for fulltext
  article indexing on a fixture;
- document remaining unproven fresh Codex and MCP registration gates in final
  artifacts instead of claiming them as complete.
