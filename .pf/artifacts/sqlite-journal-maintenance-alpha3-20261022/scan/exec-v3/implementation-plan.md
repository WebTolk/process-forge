# Scanner implementation plan

Status: implementation, exact prepared assignment, attempt 1.

1. Move the existing discovery, project filtering, native identity checks and
   temporary SQLite conflict index into the owning Core scanner. Keep the frozen
   `discover`, `rows` and `preflight` signatures and cold construction.
2. Read UTF-8 NDJSON as binary lines. Count physical, blank, filtered, valid,
   invalid, explicitly skipped and duplicate rows separately. Keep invalid bytes
   out of errors; record bounded diagnostics with line, offset, length and SHA256.
3. On explicit evidence request, exclusively create or verify identical record
   files and a deterministic manifest. Preserve every invalid byte, including NUL,
   CRLF and an unterminated last line. Refuse symlinks and conflicting evidence.
4. Verify regular source identity/signatures and full hashes before/during/after
   scanning; retain source manifests for the application import-pass comparison.
5. Add scanner-owned behavior and failure tests. Run only standard-library local
   checks in owned scratch; primary runs all registered QA and integration gates.

Inputs actually read: frozen architecture, investigation, plan, migration contract,
clarification, ADR/domain/direction (prepared inline); actual local handoff, Python
source excerpts/provenance, guidance and shared contracts. SHA256 of source
excerpts, architecture and shared contracts matches the prepared pins.

No Main/Host callback, external workplace read, Git, PF lifecycle or infrastructure
operation is part of this contribution. No other writer scope is modified.
