# Final acceptance rereview: project init local search MCP

## Verdict

Product acceptance for the reviewed slice: **pass**.

No confirmed product gap remains in the allowed source scope. The remaining incomplete live proof is an **environment-only blocker**: Codex can see and start `processforge/pf.search`, but the active Codex approval policy is `never`, so the live tool call is refused before returning a search payload.

## Verified pass

- Project initialization has a shared Core service for status, initialize, and repair. It preserves explicit `platforms`, `specializations`, and `process`, requires explicit `apply`, and limits repair to deterministic PF state.
- Snapshot producer now emits top-level `local_search_resources` as metadata-first records with `path_ref`, `load_policy: snapshot_authorized`, and `index_policy: metadata_first`.
- Private path resolution is runtime-only. `pf.search` copies the public snapshot, resolves `path_ref` into transient `content_roots`, and does not persist those roots.
- Path traversal is contained by `resolve_workspace_path_ref()` for package and registry refs.
- SQLite FTS5 lifecycle is implemented and covered: `empty`, `current`, `stale`, and stable `search_unavailable`.
- MCP stdio facade exposes `pf.search`, `pf.project_initialization.*`, and session tools; cross-project session calls fail with `session_project_mismatch`; write calls require `apply: true`; unsupported args return `invalid_arguments`.
- Template navigation is covered: authorized template search can return a private runtime `local_path`, while escaped registry content is not searchable.
- `pf.session_context` now exposes stage identity inside `work.stage_obligations`, and the acceptance smoke proves a real stage transition.
- Release registry includes both public gates: `smoke_project_init_local_search_mcp` and `smoke_project_init_acceptance`; later evidence records targeted standard-runner PASS for both.

## Environment-only blocker

`codex-mcp-registration-proof.md` shows the ProcessForge MCP server is registered and enabled, and a Codex exec session selected `processforge/pf.search`. The call failed with:

```text
MCP tool call requires approval, but approval policy is never
```

This is not evidence of a ProcessForge product defect. It blocks only the final live completed Codex MCP search result.

## Not claimed

Full extracted release/archive validation is not proven by the allowed evidence. The release smoke gates are registered and have targeted PASS evidence, but an archive-level proof would need a separate release archive run.

## Superseded blockers

Earlier artifacts recorded read-only/temp cleanup failures and missing acceptance fixture work. Those are superseded by later artifacts showing the acceptance smoke exists, passes, and Windows generated-path cleanup was remediated.

## Evidence reviewed

- `tools/smoke_project_init_local_search_mcp.py`
- `tools/smoke_project_init_acceptance.py`
- `tools/smoke_doctor_project_capability_waiver.py`
- `src/processforge_core/project_initialization.py`
- `src/processforge_core/local_resource_search.py`
- `tools/pf_runtime/mcp_server.py`
- `tools/pf_runtime/session_read.py`
- `tools/processforge.py`
- `.pf/artifacts/project-init-local-search-mcp-20260821/*`

No product code was edited.