# Minimal Workplace Example

Create a workplace outside a project:

```bash
python bin/pf.py workplace-init --workplace ./pf-workplace --apply
python bin/pf.py doctor-workplace --root ./pf-workplace
```

Expected result:

- `workplace.yaml`
- `terms.yaml`
- `registries/`
- `runtime/events/events.ndjson`

This example does not create a project `.pf/`.
