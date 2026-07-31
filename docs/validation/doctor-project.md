# Doctor Project

Doctor Project validates a ProcessForge project layer.

## Command

```bash
python bin/pf.py doctor-project --project-root <project-root>
```

Inside a linked project, prefer:

```bash
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

## Checks

- `.pf/process-forge.yaml` exists.
- `.pf/process-forge.local.yaml` exists when local workplace wiring is required.
- `.gitignore` excludes private local config and runtime paths.
- Public manifest does not contain local absolute paths.
- Workplace manifest referenced by local config exists when configured.
- ProcessForge distribution roots are used as projects only with explicit
  `processforge-development` or `processforge-core-development` type.
- Distribution, workplace, and knowledge roots inside a broad project root are
  reported and protected by role-aware scan guards.
- Project-local package resources do not produce a false resource-index warning
  when the index is optional.
- Required capability gaps distinguish registry declaration state from runtime
  proof. An explicit `.pf/artifacts/capability-waivers.yaml` entry can record
  independently verified runtime access and downgrade that gap to `WARN`.
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
