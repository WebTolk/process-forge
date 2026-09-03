# Release 1.0.2 Scope Freeze

Date: 2026-08-22
Run: `resource-indexing-release-boundary-20260822`

## IN

- Declarative `indexing` contract for ProcessForge resources.
- Workplace-owned SQLite FTS5 local search index.
- Snapshot authorization as query filter, not index ownership.
- Bounded `search-index tick` maintenance and stale detection.
- Release archive manifest/hash/order consistency gates.
- Documentation, schemas, checksums, and smoke tests required for 1.0.2 release qualification.

## OUT

- Resource marketplace.
- Remote package updater for knowledge/templates/tools.
- Resource package update URLs beyond existing update-site metadata support.
- Vector DB or embeddings.
- Full Workplace Console.
- Dynamic MCP tool-list changes by stage.
- New AI-provider adapters.
- New Director/resource-lease layer.
- Broad Python refactor unrelated to release blockers.

## Known Limitations

- Local search uses SQLite FTS5 only.
- `pf.search` returns navigation-oriented matches, not generated answers.
- Large source trees are metadata/navigation resources unless their manifest selects a bounded fulltext source.
- The configured `D:\.agents\docs\Joomla-core` production source-tree root was not present in this environment, so the production corpus benchmark is recorded as blocked.

## Release Blockers

- Release archive must be built from a clean Git source tree.
- Extracted quick/full archive validation must pass after the source commit.
- Any stale checksum or public-cleanliness failure blocks release eligibility.

## Post-1.0.2 Backlog

See `post-1.0.2-backlog.md`.
