# Project Snapshot

A project snapshot is the current machine-readable summary of a ProcessForge
project. It records the project identity, discovered files, linked workplace,
processes, resources, and context freshness.

Refresh the snapshot:

```bash
python .pf/runtime/bin/pf.py project-context-refresh --project-root .
```

Check freshness:

```bash
python .pf/runtime/bin/pf.py project-context-check --project-root .
```

The snapshot lives under `.pf/contexts/`. It is useful for handoff, agent
startup, release checks, and deciding whether the project context must be
refreshed before new work begins.
