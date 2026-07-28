# Project Context Snapshot

Project context snapshot is the computed operational map for a ProcessForge
project. It is created during project init or project refresh and is read at
session start before broad package or template scans.

Default paths:

```text
.pf/contexts/project-context.snapshot.yaml
.pf/contexts/project-context.snapshot.md
.pf/contexts/project-context.snapshots/<snapshot-id>.yaml
.pf/runtime/cache/workplace-context.snapshot.yaml
```

Commands write these files under `.pf/`; root-level context files are not the
canonical layout.

## Machine Sources

The snapshot is computed from structured sources:

- workplace and project manifests
- package and process definitions
- tool, MCP, and template registries
- assignment YAML front matter or assignment YAML
- project scan results and capability resolution

Markdown reports, logs, handoffs, reviews, and ADRs remain useful context, but
they are not the stable machine merge source. If Markdown conflicts with a
locked hard policy from the snapshot, the hard policy wins and the agent records
a conflict note or telemetry event.

## Required Fields

The YAML snapshot records:

- generated `id`
- `generated_at` and `valid_until`
- `context_requirements` copied from the project manifest
- `resolved.knowledge_resources` with instance ids, versions, generations, and fingerprints
- `freshness` and `reproducibility`
- refresh policy
- project identity
- flow root and manifest paths
- source fingerprints
- resolved hard policies and preferences
- required and optional capabilities
- selected processes, packages, templates, tools, and MCP entries
- `available_platform_contracts`, `selected_platform_contracts`,
  `platform_stack`, and `platform_selection`
- `workplace_coordination` with project mode, workplace default mode, effective
  mode, Director availability, and Director-required/inbox metadata
- session startup read order

The runtime workplace snapshot may contain local tool or MCP availability state.
It lives under `.pf/runtime/cache/` and is private.

## Platform Selection

Meta-project types such as `agent-workspace`, `brownfield-workspace`, and
`meta-workspace` can expose available platform contracts without selecting one
platform stack. In that case `selected_platform_contracts` and `platform_stack`
are empty, and `platform_selection.status` is `not_applicable`.

Normal project types, such as `joomla-extension` or `software-project`, record
selected contracts in both `selected_platform_contracts` and `platform_stack`
when a platform is declared or detected.

Use:

```bash
python bin/pf.py project-context-refresh --project-root <project-root>
python bin/pf.py project-context-check --project-root <project-root> --session-start --json
```

See [Project Context Lock Model](project-context-lock-model.md) for resource
versioning modes and capsule pinning rules.

## Evolve And Updates

When a reviewed knowledge package release from the evolve loop is applied
through the update system, impacted project context snapshots follow the normal
freshness policy. ProcessForge does not refresh snapshots silently; session
start and `project-context-check` report whether the snapshot is fresh,
fresh_with_updates, stale, or broken.
