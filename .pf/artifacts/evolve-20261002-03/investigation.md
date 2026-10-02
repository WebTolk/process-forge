# evolve-20261002-03 Investigation

Timestamp: 2026-10-02T14:23:00Z

## Finding

The current Work reproduces the task defect. `docs.python:root` is selected in
the capsule and its resolved resource still declares `index_policy: full_text`,
but the pinned Work binding is materialized as:

- `material_kind: metadata`
- `navigation: metadata_only`
- empty `manifest`

The mismatch happens before `pf.work.search` or `pf.work.resolve` read the
resource. It is created while new Work resource bindings are built.

## Root Cause

`grant_rows()` in `src/processforge_core/work_resources.py` merges
`snapshot.local_search_resources` over the resolved resource declarations. For
explicitly selected resources, `local_search_resources` can contain generated
metadata-only `indexing`, and that generated row overrides the original
declaration that still has legacy `index_policy: full_text`.

`capture_material()` then calls `metadata_descriptor()` and `_indexing()` from
`src/processforge_core/work_resource_material.py`; because the merged row now
contains metadata `indexing`, Work pins metadata-only material.

There is also a spelling gap in Work material validation:
`_indexing()` accepts legacy `fulltext`, `always_index`, and
`snapshot_authorized`, but not the public snapshot spelling `full_text`.

## Impact

Affected new capsules:

- Work resource bindings created by `build_resource_bindings()`.
- `pf.work.search` and `pf.work.resolve`, because both validate current rows
  against the pinned binding using the same `grant_rows()` and materializer.
- Prepared resources, because `prepared_resources.py` also depends on
  `grant_rows()`, `metadata_descriptor()` and `capture_material()`.

Unaffected by this task:

- Existing immutable capsules; they must not be rewritten.
- Automatic grant broadening; selected resource IDs remain unchanged.
- Explicit metadata/none policy; it must remain metadata-only/no-content.

## Proposed Direction

Within the accepted scope, keep `local_search_resources` authoritative for
grant membership and source metadata, but do not let a generated metadata-only
row erase an original full-text legacy declaration. Canonicalize legacy
`index_policy: full_text` to the fulltext material policy before validation.

`tools/processforge.py` is out of write scope because it is owned by active Work
`agent-entry-e01-e02-scoped`; if project-search producer behavior requires a
change there, it must be handled by a successor Work instead of broadening this
one.

## Evidence

- PF Work stage: `investigation`, context ready and valid.
- Reproduction: current `pf.work.resolve` for `docs.python:root` returned
  metadata-only material.
- Code inspected:
  - `src/processforge_core/work_resources.py`
  - `src/processforge_core/work_resource_material.py`
  - `src/processforge_core/local_resource_search.py`
  - `tools/smoke_work_resource_binding.py`
  - `tools/smoke_resource_indexing_policy_acceptance.py`
- Tooling gap: Serena symbol overview failed for Python files with
  `Active languages: []`; investigation used targeted shell reads after that.
