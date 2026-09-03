# Freshness Readiness Implementation Report

Дата: 2026-08-23

## Code Changes

- `tools/processforge.py`
  - added `execution_readiness_payload()`;
  - added `resource_readiness_payload()`;
  - stopped adding missing required capabilities to `broken_refs`;
  - kept `resource_readiness=blocked` as a `broken` context/search/index gate;
  - made project required capability providers workplace-aware;
  - added `readiness`, `resource_readiness`, and `execution_readiness` to snapshots/check output;
  - made `project-context-refresh` complete successfully when only execution readiness is blocked, while still returning nonzero for resource readiness blockers;
  - made manifest capability parsing read parsed YAML as well as legacy text lists.
- `tools/pf_runtime/mcp_server.py`
  - added a freshness gate for `pf.resolve` when resolving a concrete resource id.
- `tools/pf_runtime/session_read.py`
  - exposes `resource_readiness`, `execution_readiness`, and `missing_capabilities`;
  - reports execution blockers separately from context blockers.
- `tools/smoke_context_freshness_vs_execution_readiness.py`
  - reproduces fresh resources with blocked execution and proves MCP read tools work.

## Docs

Updated:

- `docs/concepts/context-freshness.md`;
- `docs/concepts/resource-search-index.md`;
- `docs/concepts/codex-session-read.md`;
- `docs/ru/concepts/context-freshness-readiness.md`.

## Security Boundary

The change is not a global bypass. Missing/corrupt snapshots, stale resource
fingerprints, stale search index state, and cross-project session mismatch still
fail closed.
