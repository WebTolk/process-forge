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
- `resolved_parameters` and `parameter_resolution` for effective structured
  parameter values
- `resolved.knowledge_resources` with instance ids, versions, generations, and fingerprints
- `freshness` and `reproducibility`
- refresh policy
- project identity
- observed `project_classification`, including status, matched classifier/rule
  ids, project types, platforms, and tags
- flow root and manifest paths
- source fingerprints
- resolved hard policies and preferences
- required and optional capabilities
- selected processes, packages, templates, tools, and MCP entries
- `active_resource_profile`, `execution_route`, and `capability_resolution`
- required capabilities, provided capabilities, satisfied requirements, and
  unsatisfied requirements as opaque ids
- `available_platform_contracts`, `selected_platform_contracts`,
  `platform_stack`, and `platform_selection`
- `workplace_coordination` with project mode, workplace default mode, effective
  mode, Director availability, and Director-required/inbox metadata
- session startup read order

The runtime workplace snapshot may contain local tool or MCP availability state.
It lives under `.pf/runtime/cache/` and is private.

## Resolved Parameters

Project context snapshots include the effective `resolved_parameters` tree and
a `parameter_resolution` block with source records, provenance, conflicts, and
status. The resolver starts from structured workplace parameters by default and
does not parse `AGENTS.md` as parameters.

Parameter merge is domain-neutral: maps merge recursively, scalar values are
replaced by more specific layers, lists of objects with `id` merge by `id`, and
lists without item ids are replaced.

Snapshots record source fingerprints for structured parameter files so changes
to workplace or project parameter sources make the snapshot stale. The Markdown
snapshot summarizes parameter namespaces and source/conflict counts; the YAML
snapshot carries the effective tree for agents and tooling.

Assignment capsules resolve assignment-level `parameters` over the pinned
project snapshot. This lets a task temporarily select or override a stand,
render preset, accounting profile, publication channel, or any other structured
parameter without changing the project snapshot.

## Platform Selection

Meta-project types such as `agent-workspace`, `brownfield-workspace`, and
`meta-workspace` can expose available platform contracts without selecting one
platform stack. In that case `selected_platform_contracts` and `platform_stack`
are empty, and `platform_selection.status` is `not_applicable`.

For ordinary projects, selected contracts are recorded in both
`selected_platform_contracts` and `platform_stack` only when workplace/project
data or an active project classifier declares a platform. Core does not infer a
platform from concrete technology filenames.

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
## Specializations And Overrides

Project-context snapshots record selected specializations and project overrides
as part of the effective context. The snapshot stores resource ids, source
paths/refs, base hashes, override hashes, merge modes, effective fingerprints,
activation or exclusion reasons, and conflicts. It must not embed full knowledge
package content.

Freshness includes specialization definitions, specialization registries,
project specialization overrides, project overrides, active tool/MCP/template
registries, active project classifiers and their observed result, process
definitions, and selected platform contracts. Existing
capsules remain pinned; new sessions should refresh or report stale context
according to policy.
