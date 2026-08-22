# Resource Catalog And Search Index Current-State Audit

## Scope

Task: `stable-mcp-resource-index-current-state-audit-20260822`

This is a read-only audit for the stable MCP resource index master prompt. No product code was changed.

## Evidence Collected

- `python tools/processforge.py project-context-check --project-root .`
  - `SNAPSHOT_ID: ctx-20260822-113651-0aea2b`
  - `STATUS: fresh`
  - `POLICY_ACTION: continue`
- SQLite probe:
  - `sqlite3.sqlite_version: 3.50.4`
  - `fts5_available`
- `python tools/smoke_project_init_local_search_mcp.py`
  - PASS: snapshot-authorized SQLite FTS5 search smoke
- `python tools/smoke_runtime_ledger_hooks_mcp.py`
  - PASS: Runtime Ledger, Codex adapter, and MCP smoke

## Current Architecture

ProcessForge already has a snapshot-authorized MCP search path, but it is an MVP project-local implementation rather than the target stable workplace-level resource index.

Current request path:

```text
pf_runtime/mcp_server.py
-> Ledger/session authorization
-> project_context_check_result
-> project_context_snapshot_paths
-> request-local path_ref resolution
-> processforge_core.local_resource_search.search
-> private local_path attached only to authorized MCP result
```

Key files:

- `tools/pf_runtime/mcp_server.py`
  - declares `pf.resolve`, `pf.search`, `pf.session_context`
  - rejects non-fresh snapshots before search
  - resolves `local_search_resources[*].path_ref` into request-local `content_roots`
  - adds `local_path` only to an authorized private MCP response
- `src/processforge_core/local_resource_search.py`
  - owns current SQLite FTS5 search implementation
  - builds `.pf/runtime/local-resource-search/search.sqlite` under each project
  - uses snapshot checksum as freshness boundary
  - rebuilds synchronously on first search or checksum mismatch
- `tools/processforge.py`
  - owns project context snapshot production
  - writes `local_search_resources` into the snapshot
  - resolves `path_ref` with containment checks
  - owns metadata-only `knowledge-index-refresh`
- `tools/pf_runtime/session_read.py`
  - owns `pf.session_context`
  - includes current work, blockers, recent activity, and stage obligations
- `tools/smoke_project_init_local_search_mcp.py`
  - proves authorized resource visibility, traversal denial, external knowledge root allowance, template search, no public absolute path leakage, and pagination ambiguity rejection
- `tools/smoke_runtime_ledger_hooks_mcp.py`
  - proves Ledger-bound `pf.session_context` access and session/project mismatch denial

## Resource Catalog State

There is no standalone stable Resource Catalog service yet.

Existing catalog-like sources are:

- workplace registries:
  - `registries/knowledge-roots.yaml`
  - `registries/package-roots.yaml`
  - `registries/templates.yaml`
  - `registries/tools.yaml`
  - `registries/mcp.yaml`
  - `registries/private-resource-paths.yaml`
- package manifests and metadata-only resource indexes
- project context snapshot `resolved.*`
- snapshot `local_search_resources`

Current `knowledge-index-refresh` is not the requested workplace-level FTS index. It writes metadata-only package `indexes/resource-index.yaml` from a package manifest and explicitly does not load heavy content.

## Snapshot Authorization State

Snapshot remains the effective authorization boundary.

The snapshot producer includes:

- `resolved.available_knowledge_resources`
- selected templates
- `local_search_resources`

`local_search_resources` is public-safe by design:

- it stores `path_ref`
- it does not persist `content_roots`, `local_path`, or `resolved_path`
- private physical paths are introduced only in a request-local runtime copy inside MCP search

`resolve_workspace_path_ref` currently enforces:

- `package: self` containment under the project root
- package resource containment under package root
- registry id lookup
- external resources as external descriptors
- only `knowledge_roots` and `private_resource_paths` may point outside the workplace root
- `relative_path` cannot escape its declared base

## Search Index State

Current index implementation:

- location: `<project>/.pf/runtime/local-resource-search/search.sqlite`
- schema: `meta`, `documents`, `documents_fts`
- FTS: SQLite FTS5
- text suffixes: `.md`, `.txt`, `.rst`, `.py`, `.json`, `.yaml`, `.yml`, `.toml`, `.ini`, `.csv`
- max file size: `1_000_000` bytes
- ranking: `bm25(documents_fts)`
- query handling: user input is treated as one literal quoted FTS phrase
- pagination: `limit`, `limitstart`, `offset`; conflicting `limitstart` and `offset` is rejected
- freshness: snapshot checksum in `meta`

Gaps against the master prompt:

- index is project-local, not workplace-level
- no separate Resource Catalog model
- no `resources` table equivalent carrying stable catalog metadata beyond document rows
- no `index_state` table with lifecycle states such as `missing`, `building`, `fresh`, `stale`, `degraded`, `failed`
- no explicit FTS5 capability probe exposed through status/doctor
- no CLI `search-index status|refresh|rebuild|doctor`
- no Runtime-owned periodic or incremental maintenance
- no add/change/delete dirty marking or fingerprint-driven refresh
- no crash recovery state for interrupted refresh
- no WAL/concurrency strategy documented in code
- no benchmark artifact
- templates are included only through snapshot `local_search_resources`; indexing remains file-content based after runtime path resolution
- tool metadata search is not implemented as an indexed kind

## MCP State

MCP tools exist:

- `pf.resolve`
- `pf.search`
- `pf.session_context`
- `pf.session_chat`
- `pf.session_activity`
- project initialization status/initialize/repair
- project/work/workplace state

Current `pf.search` correctly has no hidden global fallback. It refuses stale snapshots and searches only resources present in the authorized snapshot/runtime copy.

`pf.session_context` currently includes process/stage obligations through `stage_obligations_payload`, but it does not include the compact search readiness fields requested by the master prompt:

```yaml
search:
  status:
  generation:
  stale:
```

## Runtime Maintenance State

Runtime exists and has projection/rebuild commands, Ledger integration, and hook ingestion. The search index is not currently a Runtime-maintained service.

Current search maintenance behavior is synchronous:

- first query builds index if missing
- checksum mismatch rebuilds during query and returns `search_status: stale`
- later matching query returns `current`

This is acceptable MVP evidence, but it is not the requested periodic/incremental Runtime maintenance model.

## Security State

Confirmed by code and smoke:

- session mismatch is rejected
- project mismatch is rejected
- snapshot must be fresh
- traversal via `path_ref.relative_path` is rejected
- arbitrary workplace/global search is absent
- external knowledge root is allowed only through `knowledge_roots`
- public snapshot does not store private physical paths
- `local_path` appears only in private authorized MCP response
- `pf.project_initialization.repair` requires `apply: true`

Remaining risks:

- current project-local index can hold absolute runtime-only roots indirectly through its scanned documents, but its returned `path_ref` is synthetic `resource_id:canonical_path`; the stable design should keep public artifact boundaries explicit.
- no long-running refresh/concurrent reader model exists yet.
- no crash state distinguishes incomplete index build from fresh index beyond the final atomic replace.

## Current-State Classification By Resource Kind

| Kind | Canonical Identity Today | Registry Source | Snapshot Representation | Searchable Fields Today | Authorization Boundary |
| --- | --- | --- | --- | --- | --- |
| Knowledge resource | package/resource ids plus path_ref | package manifests, knowledge roots, package roots | `resolved.available_knowledge_resources`, `local_search_resources` | file path title and full text for supported suffixes | current session -> project -> fresh snapshot -> path_ref |
| Template | template id | `templates.yaml` | `local_search_resources` with `kind: template` | file path title and full text after path_ref resolution | current session -> project -> fresh snapshot -> templates registry containment |
| Tool metadata | tool id | `tools.yaml` | `resolved.tools` | not indexed | capability activation only; no search grant |
| MCP metadata | mcp id | `mcp.yaml` | `mcp.required/recommended/activated` | not indexed | capability activation only; no search grant |
| Process definitions | process id | process catalog | snapshot `processes.enabled` | not indexed by `pf.search` | process selection/context only |
| Specializations | specialization id | specialization registries | `selected_specializations`, `resolved_context` | not indexed by `pf.search` | process/profile selection only |

## Recommended Next Write Scopes

Do not give broad parallel write access yet.

Next safe sequence:

1. `resource-search-index-design`
   - write only:
     - `.pf/artifacts/stable-mcp-resource-index-20260822/resource-search-index-design.md`
     - `.pf/artifacts/stable-mcp-resource-index-20260822/resource-search-index-schema.md`
     - `.pf/artifacts/stable-mcp-resource-index-20260822/index-maintenance-design.md`
     - `.pf/artifacts/stable-mcp-resource-index-20260822/full-mcp-acceptance-test-plan.md`
2. `resource-catalog-core-slice`
   - likely write:
     - new or updated Core catalog/search service under `src/processforge_core/`
     - focused tests under `tools/smoke_*`
   - exact files should be chosen after design review.
3. `search-index-cli-slice`
   - likely write:
     - `tools/processforge.py`
     - focused CLI smoke
4. `search-index-runtime-maintenance-slice`
   - likely write:
     - `tools/pf_runtime/*`
     - runtime maintenance smoke
5. `search-index-mcp-session-context-slice`
   - likely write:
     - `tools/pf_runtime/mcp_server.py`
     - `tools/pf_runtime/session_read.py`
     - MCP/session smokes
6. `search-index-docs-and-review`
   - likely write:
     - `docs/concepts/runtime-mcp.md`
     - `docs/concepts/resource-management.md`
     - RU mirrors
     - independent review artifacts

## Blockers Before Product Implementation

- Design must decide whether to evolve `src/processforge_core/local_resource_search.py` or introduce a new workplace-level service while preserving the old smoke contract during migration.
- Need explicit storage location under workplace runtime, not project `.pf/runtime/local-resource-search`.
- Need lifecycle/doctor contract before CLI and MCP expose status.
- Need concurrency model before Runtime background maintenance.
- Need benchmark corpus and acceptance fixture definition.

## Recommended First Implementation Slice

Start with design and schema, not code:

1. Design the stable Resource Catalog as a derived view over existing registries/manifests/snapshots.
2. Design the workplace-level SQLite schema with `resources`, `documents`, `documents_fts`, and `index_state`.
3. Define CLI status/refresh/rebuild/doctor response shape.
4. Define migration compatibility from project-local MVP search to workplace-level index.
5. Define acceptance fixture for authorized A/B, unauthorized C, template T, add/change/delete, pagination, crash, and external root traversal.

Only after that should product edits start.
