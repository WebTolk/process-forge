# Handoff: first-run-python-cli-hardening -> next maintainer

Objective:
Make first-run linked-project commands Python-first and runnable from the project root.

Current status:
Implementation is ready for review and validation gates pass.

Input artifacts:
- `задания/processforge_first_run_python_cli_hardening_master_prompt.md`
- `.pf/artifacts/first-run-processes-report.md`

Files changed:
- `tools/processforge.py`
- `tools/smoke_first_run.py`
- `bin/pf.py`
- `bin/pf`
- `bin/pf.bat`
- docs and prompts for first-run launcher guidance
- process definitions and validation file lists

Files not to touch:
- `.pf/runtime/`
- `.pf/process-forge.local.yaml`
- external workplace registries

Known issues:
- `--interactive` is non-prompting.
- `pf` requires PATH setup unless `.pf/runtime/bin/pf.py` is used.

Required checks:
- `python tools/smoke_first_run.py`
- `python tools/processforge.py release-check --root .`
- `python tools/smoke_resource_management.py`
- `git diff --check`

Next recommended action:
Review whether a packaged `pf` install path is needed after the file-only MVP.
