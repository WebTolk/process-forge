# Resource Management

Resource changes that affect knowledge packages, resources, templates, tools,
platform contracts, or update sources can invalidate project context snapshots.
After applying or rolling back such changes, ProcessForge marks impacted
projects stale so the next `project-context-check` can apply the project
`context_policy`.

Delivery/build profiles are reusable operation resources. They can be attached
to a software lifecycle run through `execution_profile.delivery_profile`, but
they should not be modeled as separate public core process ids.

Resource Management is the workplace-surface layer for adding and maintaining knowledge packages, knowledge resources, documentation packages, templates, tools, MCP providers, platform contracts, and process templates.

The layer is proposal-first. Commands may write proposal/report artifacts under `runtime/resource-management/` in dry-run mode, but package manifests, indexes, registries, and contracts are updated only with `--apply`.

## Boundaries

- Workplace files may contain local registry paths because the workplace is private to the machine.
- Project public files must not contain private absolute paths.
- Linked mode keeps global resources in the workplace and exposes only selected indexes through project snapshots.
- Heavy content is not loaded into prompts; agents consume resource indexes and request specific files on demand.

## Current Create And Doctor Commands

- `knowledge-package-create`
- `knowledge-package-doctor`
- `template-create`
- `template-doctor`
- `platform-create`
- `platform-contract-doctor`

## Proposal, Update, And Registry Commands

- `knowledge-add-url`
- `knowledge-add-resource`
- `knowledge-index-refresh`
- `docs-import-plan`
- `template-add`
- `tool-register`
- `mcp-register`
- `platform-contract-install`
- `update entity-sources rebuild`
- `update candidates refresh`
- `update notifications list`
- `update stage`
- `update apply --confirm`
- `update rollback`

Resource manifests can declare `update_sites`; see `docs/concepts/update-sites.md`
and `docs/concepts/update-lifecycle.md`. Runtime update caches, staged artifacts,
backups, and notifications live under `runtime/update/` and are not public
archive content.

## Events

Resource operations emit workplace events to `runtime/events/events.ndjson`. Hooks may route those events to outbox files, but network sending remains a future explicit mode.
