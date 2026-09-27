# T02 investigation and impact

Reproduced through real source MCP in an isolated temporary Workplace/project: registered A/B; selected A; created Work; changed selection to B using normal project refresh. Work state still pins A, project resolve(A) denies, resolve(B) and B search succeed, original capsule bytes unchanged. Before.json and reproduce-before.py retain exact evidence; fixture removed by its context manager. This confirms missing Work-bound navigation, not a bypass of current project authorization.

Current Garage search checks freshness and maintains a shared Workplace index, then queries resource IDs from today's project snapshot (garage.py ResourceSearchService). Resolve likewise selects today's resource. The shared DB may be fresh with no indexed documents for project-local grants. Its declared resource fingerprints often hash metadata only, and file verification regenerates today's documents. It cannot alone prove that a result is the material pinned to an old Work.

ProcessExecutionService._write_capsule currently pins only selected IDs and process/snapshot identities. _select_work may prefer the most recently updated record and ignores a supplied run when assignment is supplied. A new resource API must require and check exact selectors independently, not inherit that convenience selection. Existing Work stage transitions preserve pinned process and capsule; resource reads need their own checksum/identity verification without changing old lifecycle behavior.

Existing indexing source policy defines metadata/fulltext/none, include/exclude, text suffixes and path containment. Work material binding can reuse policy normalization, but needs explicit bounded traversal, byte hashes, no silent unreadable/oversize omissions, and a portable manifest. Metadata resources bind their declaration, not their entire mutable source/output tree. Fulltext results need exact verified files, not shared cache rows selected only by resource ID.

Junior worker-resource-map.md supplies exact source/fixture references. Primary inspected Garage, process selectors/capsule writer, MCP routing/schema, CLI work entry points and evidence normalization. Evidence dictionaries retain additive provenance fields, so resource proof can be attached to an artifact without changing mandatory event/evidence schema.

Impact: additive versioned capsule binding, exact Work service/selectors, source CLI/MCP routes and current-project scope/coverage metadata. Existing project API and old capsules remain readable. Restricted Work reads of old capsules return legacy_contract_incomplete; no guessed material baseline or overwrite. T03 will reuse binding construction in the shared full capsule builder. T09 diagnostics capture reason/identity metadata only.

No platform domain overlay applies; repository Python contracts and local docs consulted. Serena symbol extraction failed with no active languages, bounded UTF-8 reads used. No source code changed during investigation.
