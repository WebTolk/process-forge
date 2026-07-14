# Project Context Snapshot

Project context snapshot is the computed operational map for a ProcessForge
project. It is created during project init or project refresh and is read at
session start before broad package or template scans.

Default paths for new projects:

```text
.pf/contexts/project-context.snapshot.yaml
.pf/contexts/project-context.snapshot.md
```

Legacy root-layout projects may keep the same filenames under `contexts/` until
a migration is reviewed.

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
- session startup read order

Use:

```bash
python tools/processforge.py project-context-refresh --project-root <project-root>
python tools/processforge.py project-context-check --project-root <project-root>
```
