# Independent Architecture Review

Дата: 2026-08-23

Status: pass after remediation.

## Local Pre-Review

The architecture boundary is coherent:

- snapshot remains the resolver and authorization source;
- readiness is a projection over existing capability/resource resolution;
- missing capabilities are not treated as providers;
- read-only MCP tools check only their own prerequisites;
- stale/broken resources still use existing freshness and index gates.

## Delegated Reviewer Findings

Reviewer found:

- High: `pf.resolve` bypassed freshness and could resolve from stale/broken snapshots.
- Medium: `pf.session_context` treated `fresh_with_updates` as a context blocker.
- Low: the new smoke did not cover the fail-closed negative path.

## Remediation

- Added `pf.resolve` resource-id freshness gate in `tools/pf_runtime/mcp_server.py`.
- Treated `fresh_with_updates` as accepted freshness in `pf.session_context`.
- Extended `smoke_context_freshness_vs_execution_readiness.py` with stale
  `pf.resolve` negative coverage.

## Result

PASS.
