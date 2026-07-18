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

This process does not create `.pf/` in a project and does not select a project type.
