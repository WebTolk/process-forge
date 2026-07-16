# Minimal Workplace Example

Create a workplace outside a project:

```bash
python tools/processforge.py workplace-init --workplace ./pf-workplace --apply
python tools/processforge.py doctor-workplace --root ./pf-workplace
```

Expected result:

- `workplace.yaml`
- `terms.yaml`
- `registries/`
- `runtime/events/events.ndjson`

This example does not create a project `.pf/`.
