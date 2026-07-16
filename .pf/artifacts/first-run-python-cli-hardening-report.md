# First-Run Python CLI Hardening Report

## Status

ready_for_review

## START_AGENT_HERE Fix

Generated `.pf/START_AGENT_HERE.md` no longer recommends a project-root `tools/processforge.py` command. It now uses:

- `pf doctor-project --project-root .`
- `python .pf/runtime/bin/pf.py doctor-project --project-root .`

## Canonical Launcher

Python CLI is canonical:

- distribution entrypoint: `tools/processforge.py`
- cross-platform wrapper: `bin/pf.py`
- convenience wrappers: `bin/pf`, `bin/pf.bat`

Only Python plus thin shell/cmd launchers are part of the release surface.

## Local Project Launcher

`project-onboard --apply` creates:

- `.pf/runtime/bin/pf.py`
- `.pf/runtime/bin/pf`
- `.pf/runtime/bin/pf.bat`

The launcher reads private `.pf/process-forge.local.yaml` and falls back to `PROCESSFORGE_HOME`. It calls the distribution CLI without exposing resolved local paths in public project files.

## Doctor Hardening

- `workplace-init --apply` runs `doctor-workplace`, emits workplace doctor events, and writes workplace report/review/handoff.
- `project-onboard --apply` runs `doctor-project`, emits project doctor events, and appends doctor output to the onboarding report.

## Docs Updated

- `README.md`
- `QUICKSTART.md`
- `docs/getting-started.md`
- `docs/getting-started/first-run.md`
- `docs/getting-started/project-onboarding.md`
- `docs/getting-started/agent-prompts.md`
- `docs/concepts/workplace-vs-project.md`
- `docs/release-checklist.md`
- first-run agent prompts

## Tests Passed

- `python -m py_compile tools/processforge.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/validate-process-forge-checksums.py --root . --check`
- `python tools/smoke_first_run.py`
- `python tools/smoke_resource_management.py`
- `python tools/processforge.py doctor-project --project-root .`
- `python tools/processforge.py events-validate --project-root .`
- `python tools/processforge.py release-check --root .`
- `git diff --check`

## Limitations

- `--interactive` remains accepted but non-prompting in the file-only MVP.
- `pf` still requires PATH setup unless the project-local `.pf/runtime/bin/pf.py` fallback is used.
