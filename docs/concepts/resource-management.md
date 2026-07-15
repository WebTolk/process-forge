# Resource Management

Resource Management is the workplace-surface layer for adding and maintaining knowledge packages, knowledge resources, documentation packages, templates, tools, MCP providers, platform contracts, and process templates.

The layer is proposal-first. Commands may write proposal/report artifacts under `runtime/resource-management/` in dry-run mode, but package manifests, indexes, registries, and contracts are updated only with `--apply`.

## Boundaries

- Workplace files may contain local registry paths because the workplace is private to the machine.
- Project public files must not contain private absolute paths.
- Linked mode keeps global resources in the workplace and exposes only selected indexes through project snapshots.
- Heavy content is not loaded into prompts; agents consume resource indexes and request specific files on demand.

## MVP Commands

- `knowledge-add-url`
- `knowledge-add-resource`
- `knowledge-index-refresh`
- `knowledge-package-doctor`
- `docs-import-plan`
- `template-add`
- `tool-register`
- `mcp-register`
- `platform-contract-install`

## Events

Resource operations emit workplace events to `runtime/events/events.ndjson`. Hooks may route those events to outbox files, but network sending remains a future explicit mode.
