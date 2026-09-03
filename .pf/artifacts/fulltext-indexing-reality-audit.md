# Fulltext Indexing Reality Audit

Generated: 2026-08-24 12:00 +04

## Finding

The search-index service is operational but empty for the current project
snapshot:

- SQLite is available: `3.50.4`;
- FTS5 is available;
- index status is `fresh`;
- resource count is `0`;
- document count is `0`.

This means the current project has search infrastructure readiness but not
content-corpus readiness.

## Interpretation

The previous Garage test symptom, where broad resource discovery could show
available roots while exact text queries returned zero matches, is consistent
with a gap between resolved resources and indexable article/content roots. The
index should not be treated as semantically ready merely because it is fresh.

## Required Gate

Acceptance must include a temporary Git project with a real indexed article and
a query for unique article text. The expected outcome is at least one result
with a bounded resource id and canonical relative path.

Status: `confirmed_gap_with_fixture_required`.
