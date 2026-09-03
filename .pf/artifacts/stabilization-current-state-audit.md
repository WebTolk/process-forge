# Garage/Forge Stabilization Current-State Audit

Date: 2026-08-24
Run: `stabilization-garage-forge-20260824`
Task: `stabilization-baseline-audit-20260824`
Source prompt: `задания/process-forge-stabilization-garage-forge-master-prompt.md`

## Baseline

- Branch state before this run: `dev...origin/dev`.
- Pre-existing dirty files before this run: `.pf/artifacts/projections/command-history.md`, `.pf/artifacts/projections/stage-obligations.json`, outside-audit Markdown and CSV artifacts under `.pf/artifacts/`.
- This run created `.pf/runs/stabilization-garage-forge-20260824/`, `.pf/assignments/stabilization-baseline-audit-20260824.yaml`, and `.pf/contexts/assignment-capsules/stabilization-baseline-audit-20260824.capsule.yaml`.
- Initial assignment capsule creation was blocked because the project context snapshot was stale: `workplace_manifest` and `workplace-mcp-registry-registries-mcp-yaml` changed.
- `project-context-refresh --reason stabilization-garage-forge-baseline` restored `STATUS: fresh` and performed bounded search-index maintenance for this project.

## Current Mechanisms

- Codex hook installation exists as `tools/pf_runtime/codex_integration.py`. It manages only project-local `.codex/hooks.json`, supports `status/install/remove`, backs up existing hook files, merges managed handlers without deleting operator hooks, and has a focused smoke in `tools/smoke_codex_integration.py`.
- Codex hook ingestion exists as `tools/pf_runtime/codex_hooks.py`. It maps Codex lifecycle events to raw envelopes, sends to Runtime `/event` when available, and falls back to durable Host/Core ingestion when Runtime is unavailable.
- Session identity comes from Codex hook payload `session_id`; `codex_hooks.py` does not invent a new id. It can return a `SessionStart` additional context with the already Ledger-bound id.
- Raw ingress and conversation materialization are centralized in `tools/pf_runtime/host.py`; the adapter stays thin.
- MCP session authorization is in `tools/pf_runtime/mcp_server.py` and `tools/pf_runtime/session_read.py`. Session read tools fail with structured `missing_session`, `unknown_session`, `session_project_mismatch`, and related stable codes.
- `pf.search` is read-only at query time. It rejects stale aggregate context with `snapshot_not_fresh` and uses `ResourceSearchIndex.search()` without rebuilding inside the search call.
- Search maintenance exists in `search_index_maintenance_for_known_projects()` and `ResourceSearchIndex.maintenance_tick()`. It ran successfully during `project-context-refresh`, but MCP stdio startup does not currently perform a bounded bootstrap maintenance pass before serving tools.
- Current-session projection is written by `write_current_session_refs()` during agent check-in, heartbeat, and checkout. Stale presence updates mark presence stale but do not rewrite the current-session projection in the observed code path.
- Capability provider registration and maintenance are present through `tool-register`, `mcp-register`, snapshot resolution, and `execution_readiness.missing_capabilities`; missing providers are reported rather than faked.
- `doctor-project` checks `.gitignore` by literal substring for `.pf/process-forge.local.yaml`, `.pf/runtime/`, and `.pf/cache/`.

## Confirmed Gaps

1. Project initialization diagnostics do not expose Codex integration state.
   `project_initialization.status()` reports snapshot, workplace, resources, MCP, and deterministic artifacts, but not project-local hook target state, managed event coverage, global hook state, or restart-required semantics.

2. `project-init-repair` cannot install or repair Codex hooks.
   The current repair actions are only `refresh_context` and `restore_deterministic_artifacts`; this leaves the hook installer as a separate utility rather than part of the expected project initialize/repair path.

3. `doctor-project` can false-fail `.gitignore` protection.
   It uses literal text checks. A `.gitignore` containing `.pf/` effectively protects `.pf/process-forge.local.yaml`, but the doctor still reports a hard missing exact entry.

4. MCP Garage bootstrap is incomplete.
   MCP startup resolves Runtime/Core and then serves requests. It does not run bounded context/search maintenance before serving. `pf.search` correctly avoids hidden rebuild, but a fresh Garage session can still receive a blocker that requires a manual CLI refresh.

5. Search readiness is not yet a first-class structured MCP response.
   `pf.session_context` includes a compact `search` projection, and `pf.search` returns index state on stale index, but there is no explicit `search_readiness` object separating session, resource authorization, snapshot, and index prerequisites.

## Scoped Implementation Choice

The first implementation slice should avoid a second engine and should use the existing services:

- extend `project_initialization.status/repair` with Codex hook status and `install_codex_hooks`;
- update `doctor-project` to classify effective Git protection as PASS and exact-policy absence as WARN;
- add focused smokes for the two confirmed defects;
- document remaining MCP bootstrap/search-readiness gaps as residual acceptance blockers if not completed in this slice.
