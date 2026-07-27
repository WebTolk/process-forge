# Project Context Snapshot

Project context snapshot is the computed operational map for a ProcessForge
project. It is created during project init or project refresh and is read at
session start before broad package or template scans.

Default paths:

```text
.pf/contexts/project-context.snapshot.yaml
.pf/contexts/project-context.snapshot.md
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

- `generated_at` and `valid_until`
- refresh policy
- project identity
- flow root and manifest paths
- source fingerprints
- resolved hard policies and preferences
- required and optional capabilities
- selected processes, packages, templates, tools, and MCP entries
- `workplace_coordination` with project mode, workplace default mode, effective
  mode, Director availability, and Director-required/inbox metadata
- session startup read order

The runtime workplace snapshot may contain local tool or MCP availability state.
It lives under `.pf/runtime/cache/` and is private.

Use:

```bash
python bin/pf.py project-context-refresh --project-root <project-root>
python bin/pf.py project-context-check --project-root <project-root>
```
