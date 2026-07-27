# Workplace Initialization

Workplace initialization is run once per machine, device, server, or runner host.

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
