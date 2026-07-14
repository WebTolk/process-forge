# Doctor Project

Doctor Project validates a ProcessForge project layer.

## Command

```bash
python tools/processforge.py doctor-project --project-root <project-root>
```

## Checks

- `.pf/process-forge.yaml` exists, or a legacy root manifest exists.
- `.pf/process-forge.local.yaml` exists for new `.pf` projects.
- `.gitignore` excludes private local config and runtime paths.
- Public manifest does not contain local absolute paths.
- Workplace manifest referenced by local config exists when configured.
- Project package draft exists.
- Init artifacts exist.
- Init review exists.

## Result Format

```text
PASS: .pf/process-forge.yaml found
PASS: .gitignore contains .pf/runtime/
FAIL: workplace manifest is missing
```

The command exits with a non-zero code when any `FAIL` result exists.
