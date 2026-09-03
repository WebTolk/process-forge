# Search Relevance Audit

Generated: 2026-08-24 12:00 +04

## Finding

`pf.search` is implemented as a navigation/search adapter over a prebuilt local
resource index. It does not refresh the index during query execution and should
not fall back to arbitrary workplace, web, or global search.

The current project index is fresh but empty. A content query can therefore
correctly return no matches while the system still reports infrastructure
freshness.

## Required Product Distinction

Garage readiness needs two separate signals:

- infrastructure readiness: snapshot fresh, SQLite/FTS available, index fresh;
- semantic corpus readiness: at least one authorized indexable resource and at
  least one indexed document when the project expects local search.

Status: `design_gap`.
