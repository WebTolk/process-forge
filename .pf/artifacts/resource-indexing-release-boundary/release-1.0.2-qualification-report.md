# Release 1.0.2 Qualification Report

## Current Qualification

Qualified for the resource-indexing release boundary.

## Passed

- `release-check`
- schema validation
- public cleanliness
- checksum inventory after refresh
- local search/MCP smokes
- indexing-policy acceptance smoke
- privacy sanitizer smokes
- clean-source `release-pack`
- release archive contract/freshness quick validation
- full extracted archive public validation
- extracted archive resource-indexing policy acceptance smoke
- extracted archive project-init/local-search MCP smoke

## Release Artifact

- Archive: `dist/processforge-1.0.2-resource-indexing-20260822.zip`
- Manifest: `dist/processforge-1.0.2-resource-indexing-20260822.manifest.json`
- Entries: `865`
- SHA-256: `61400bd0f267bf3c3abb9e74fec210be34cee1418da7769d9d91404661c23f50`
- Source commit: `47e87756138b0fd662caf3a790402e9557414e03`

## Full Gate Resolution

- Full extracted `release-archive-test --extracted-test full --timeout-scale 2` completed with `RESULT: PASS` in `969.61` seconds.
- The resumed investigation found the earlier interruption was premature. `smoke_long_lived_runtime.py` passed standalone and inside the full public suite.
- The actual public-suite defect was stale `smoke_project_init_acceptance.py` expectations for query-time search rebuild; the smoke now follows maintenance-owned refresh and degraded SQLite capability semantics.

## Release Boundary

After this implementation, only release blocker fixes, security/data-loss fixes, critical MCP/search correctness fixes, packaging/update fixes, docs, and tests are allowed before 1.0.2.
