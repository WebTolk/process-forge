# evolve-20261002-03 Domain Modeling

Timestamp: 2026-10-02T14:30:00Z

## Domain Objects

Resolved resource declaration:
- Comes from `snapshot.resolved.knowledge_resources`.
- Owns the declared resource identity and policy.
- May express policy as explicit `indexing` or legacy `index_policy`.

Local search resource row:
- Comes from `snapshot.local_search_resources`.
- Defines the authorized project/search allowlist and operational resource data.
- May carry generated `indexing` used by project search.

Work material row:
- Derived by `grant_rows()`.
- Used to create immutable `resource_bindings`.
- Must preserve the selected resource grant set while materializing the same
  declared policy that the resolved declaration exposes.

Pinned Work binding:
- Immutable after capsule creation.
- Stores metadata and material fingerprints, material kind and manifest.
- Existing bindings are verified, not silently migrated.

## Policy Rules

1. Grant membership is still determined by `local_search_resources` when that
   list exists; an empty list remains an empty allowlist.
2. A resolved declaration's explicit `indexing` is authoritative for Work
   materialization.
3. A resolved declaration's recognized legacy `index_policy` is authoritative
   when explicit `indexing` is absent.
4. Legacy full-text aliases include `fulltext`, `full_text`,
   `always_index`, and `snapshot_authorized`.
5. Legacy metadata aliases include `metadata`, `metadata_first`,
   `index_only`, `source_tree`, and `symbols`.
6. Legacy none aliases include `none`, `never`, and `disabled`.
7. A generated metadata-only local-search policy must not downgrade an original
   full-text declaration.
8. Explicit metadata/none must not be broadened to full-text.
9. Old capsules are not rewritten; only new bindings receive corrected
   materialization.

## Impact Rules

- `build_resource_bindings()` should pin corrected material for new Work.
- `WorkResourceService.read()` should validate current material using the same
  corrected row construction.
- Prepared resources should inherit the behavior because they use the same Core
  resource material path.
- If the project-search producer still writes an incorrect generated policy,
  that producer remains a separate scoped change because `tools/processforge.py`
  is out of this Work's write scope.

## Acceptance Model

The focused acceptance fixture should prove:

- Registry -> selection -> snapshot -> capsule -> `work.search`/`work.resolve`
  preserves legacy `index_policy: full_text` as full-text material.
- The full-text binding has a non-empty manifest and verified material
  navigation.
- Explicit metadata still resolves as metadata and does not expose changed body
  text through Work search.
- Existing stale/revoked/material-change negative cases continue to pass.
