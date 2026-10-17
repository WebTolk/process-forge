# Read/cache domain rules

File bytes remain authoritative. A parse cache is derived, process-local memory and grants no access, validation or readiness decision. Each caller still reads current content; hashes/capsule fingerprints/symlink/containment/budget checks stay with their existing owners. Content changed with identical size/mtime is a new input. Missing/recreated files retain existing read behavior. No persistent cache database or hidden read-side file writes.

Parser policy is part of identity: selected safe loader, parser and constructor/resolver rules. Unsafe or changed custom policy must not reuse an old result. Parse failures and fallback results are not shared across requests. No cached permissions, inventory completeness, terminal lifecycle decision or error envelope.

Returned data must remain independent: callers can mutate dictionaries/lists without poisoning other requests. YAML aliases and cycles within a result retain their relationships. Cache snapshots stay private. Only ordinary safe built-in values are retained; unsupported custom objects bypass shared retention.

Common full-document reads retain their complete payload. Run discovery is a distinct small projection (id/status/__yaml_error__) over a completely validated input; it preserves sorting, status filtering, missing-id fallback and invalid-YAML skips. Full/history-bearing data remains on disk and available to authoritative full reads.

Memory is bounded by weighted LRU and entry count; projections of large inputs retain only a digest/policy and selected data, never the complete input text/history. Current per-request limits remain independently bounded. Cache races may duplicate cold parsing but must not corrupt accounting or mutable snapshots; independent cache misses must not hold a global lock during YAML parsing.
