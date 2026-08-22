# Resource Indexing Policy Audit

Date: 2026-08-22

## Findings

- Previous local search DB schema was snapshot/scope-oriented (`scope_key` on documents).
- Previous `search()` could build or rebuild the index during a query, which could hide stale state.
- Existing resource metadata used legacy `index_policy` strings.
- Runtime maintenance existed as bounded `search-index tick`, but the indexed document model still duplicated by snapshot scope.

## Confirmed Fixes

- `src/processforge_core/local_resource_search.py` now uses schema version 3 with resource-oriented `resources`, `documents`, `documents_fts`, and `index_state`.
- New `schemas/resource-indexing.schema.json` defines reusable `fulltext`, `metadata`, and `none` policy.
- Snapshot production in `tools/processforge.py` emits explicit `indexing` policies for local search resources and templates.
- `pf.search` reports missing/stale/degraded status without hidden refresh.

## Evidence

- `python tools/validate-process-forge-schemas.py --root .` PASS.
- `python tools/smoke_resource_indexing_policy_acceptance.py` PASS.
- `python tools/smoke_project_init_local_search_mcp.py` PASS.
- `python tools/smoke_search_update_operational_hardening.py` PASS.
