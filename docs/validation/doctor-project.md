# Doctor Project

Doctor Project validates a ProcessForge project layer.

## Command

```bash
python tools/processforge.py doctor-project --project-root <project-root>
```

## Checks

- `process-forge.yaml` exists.
- `process-forge.local.yaml` exists.
- `.gitignore` excludes private local config.
- Public manifest does not contain local absolute paths.
- Workplace manifest referenced by local config exists.
- Project package draft exists.
- Init artifacts exist.
- Init review exists.

## Result Format

```text
PASS: process-forge.yaml found
PASS: process-forge.local.yaml is ignored
FAIL: workplace manifest is missing
```

The command exits with a non-zero code when any `FAIL` result exists.
