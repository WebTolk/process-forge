# evolve-20261002-03 Architecture Plan

Timestamp: 2026-10-02T14:35:00Z

## Architecture

Use the existing Work resource materialization path as the single enforcement
point for new Work bindings and Work-scoped reads:

- `grant_rows()` builds the material rows used by binding creation and reads.
- `metadata_descriptor()` and `capture_material()` canonicalize and fingerprint
  those rows.
- Prepared resources already use these same Core functions, so no separate
  prepared-resource branch is needed.

The change stays inside the accepted scope and does not alter immutable
capsules, process definitions, selected resource IDs, or runtime services.

## Implementation Plan

1. Add a small policy classifier in `work_resources.py`.
   - Detect explicit `indexing` on the resolved declaration.
   - Detect recognized legacy `index_policy`, including `full_text`.
   - Re-apply the resolved declaration's policy after merging the local search
     row, so generated metadata does not downgrade full-text declarations.
2. Harden `_indexing()` in `work_resource_material.py`.
   - Accept `full_text` as a legacy full-text spelling.
   - Canonicalize it before calling the shared normalizer.
3. Extend `smoke_work_resource_binding.py`.
   - Add a registry/selection/snapshot/capsule/work.search/work.resolve
     fixture for legacy `index_policy: full_text`.
   - Keep the existing explicit metadata negative behavior.
4. Update EN/RU Work-resource documentation.
   - Document that Work materialization preserves resolved declaration policy
     precedence and does not rewrite old capsules.

## Decision Log

- Keep grant membership controlled by `local_search_resources`; this preserves
  the established allowlist contract, including the valid empty allowlist case.
- Treat resolved resource policy as authoritative for Work materialization when
  the resolved declaration includes explicit `indexing` or recognized legacy
  `index_policy`.
- Do not edit `tools/processforge.py` in this Work because PF reports an active
  write owner for that file.
- Do not edit `local_resource_search.py` in this Work because it is outside the
  accepted write scope. If project-search producer behavior still needs a
  product change after this Core fix, record it as a scoped residual item.

## Verification Plan

- Python compile check for changed Python files.
- `tools/smoke_work_resource_binding.py`.
- `tools/smoke_resource_indexing_policy_acceptance.py`.
- `git diff --check` on scoped product/docs/test files.
