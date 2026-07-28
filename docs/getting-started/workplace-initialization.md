# Workplace Initialization

Workplace initialization is run once per machine, device, server, or runner host.
For human-led setup of a new machine, prefer
[Guided workplace setup](guided-workplace-setup.md); use this direct command
path for fully automatic setup or when the setup answers are already known.
Fully automatic setup starts with an optional read-only device-discovery stage:
the agent inspects accessible `AGENTS.md`, skills, local docs, platforms,
toolchains, tools, MCP configuration, and project roots, then proposes which
ProcessForge entities to create or register before apply.

It creates:

- `workplace.yaml`
- `terms.yaml`
- `registries/`
- `knowledge/`
- `packages/`
- `reusable-templates/`
- `tools/`
- `mcp/`
- `runtime/events/events.ndjson`

Command:

```bash
python bin/pf.py workplace-init --workplace ./pf-workplace --apply
python bin/pf.py doctor-workplace --root ./pf-workplace
```

Workplace coordination is capability-level. Enabling Director support makes a
workplace organized-capable, but projects still choose their own mode:

```yaml
coordination:
  director_enabled: true
  director_office_enabled: true
  default_project_mode: simple
```

Useful commands:

```bash
python bin/pf.py workplace-mode status --workplace ./pf-workplace
python bin/pf.py workplace-mode set --workplace ./pf-workplace --director-enabled true --director-office-enabled true
python bin/pf.py workplace-mode set-default-project-mode --workplace ./pf-workplace --mode simple
python bin/pf.py workplace-mode doctor --workplace ./pf-workplace
```

This process does not create `.pf/` in a project and does not select a project type.

For automatic setup, apply starts only after the operator approves the automatic
setup proposal produced from device discovery. If broad disk access is not
available, the agent uses the configured fallback scope rather than scanning the
whole device.

Heavy local documentation should be registered as `knowledge_roots.local-docs`.
The root may live near the workplace on disk, but project source scans treat it
as external knowledge rather than project source.
