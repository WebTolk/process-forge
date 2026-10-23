# Selected-resource indexing: metadata and unavailable roots

Actual red probes of the new selective route found two silent-success edges:
external URL references have no local root and therefore previously produced no
FTS metadata document; unavailable local roots also produced zero indexed rows.
The batch's documented URL example requires actual metadata indexing without a
download. For external_resources references with metadata-only policy and no
fulltext sources, use the operation's existing root solely as a metadata anchor.
No directory walk/body open/network request is permitted. This applies through
the shared backend so a later full pass retains the same external metadata.

Before a selected pass, require every enabled selected resource to resolve an
authorized indexable root. A missing local root fails with a portable diagnostic;
it cannot silently be counted as successfully indexed. Disabled/none policies
are intentional exclusions, and their selected cached rows must be removed
transactionally while all unselected rows stay intact. The selection remains
explicit, qualified and non-workplace; it cannot acknowledge global invalidation.

Only the already-authorized primary local_search/index_maintenance/regression
scope changes. Preserve native authoring and metadata-only/fulltext exclusions.
Retain red probes and repeat full QA/native independent review before delivery.
