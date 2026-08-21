# Start Agent Here

You are working inside a ProcessForge-enabled project.

## First Steps

1. Read `.pf/AGENTS.md`.
2. Read `.pf/contexts/project-context.snapshot.yaml`.
3. Read the active assignment in `.pf/assignments/`.
4. Run:

```bash
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

If `pf` is available in PATH, this short form is also acceptable:

```bash
pf doctor-project --project-root .
```

5. If doctor fails, report the failures and propose safe fixes.
6. Do not expose local absolute paths from `.pf/process-forge.local.yaml`.
7. Use ProcessForge artifacts, reviews, and handoffs for outputs.
8. Do not call a distribution-local CLI path from this project root unless this project is the ProcessForge distribution itself.

## Current Assignment

- File: `.pf/assignments/first-assignment.yaml`
- Goal: Verify ProcessForge project onboarding for `process-forge`.

## Useful Commands

```bash
python .pf/runtime/bin/pf.py project-context-refresh --project-root .
python .pf/runtime/bin/pf.py assignment-capsule --project-root . --assignment .pf/assignments/first-assignment.yaml
python .pf/runtime/bin/pf.py hooks-dispatch --project-root . --event-type project.onboarding.completed --dry-run
```
