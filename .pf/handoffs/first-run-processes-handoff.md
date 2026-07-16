# Handoff: first-run-processes -> next maintainer

Objective:
Ship a file-only first-run UX for ProcessForge.

Current status:
Implementation is ready for review and validation gates pass.

Input artifacts:
- `задания/processforge_first_run_processes_master_prompt.md`
- `.pf/AGENTS.md`
- `.pf/process-forge.yaml`

Files changed:
- `tools/processforge.py`
- `processes/workplace-initialization.yaml`
- `processes/project-onboarding.yaml`
- `prompts/`
- `docs/getting-started/`
- `docs/concepts/workplace-vs-project.md`
- `examples/first-run/`
- `bin/`
- `tools/smoke_first_run.py`
- validation/checksum files
- `.pf/artifacts/first-run-processes-report.md`
- `.pf/reviews/first-run-processes-review.md`
- `.pf/handoffs/first-run-processes-handoff.md`

Files not to touch:
- `.pf/runtime/`
- `.pf/process-forge.local.yaml`
- workplace-local registries outside an explicit workplace task

Known issues:
- `--interactive` is currently accepted but non-prompting.
- Minimal project doctor may warn about missing project knowledge resource index.

Required checks:
- `python -m py_compile tools/processforge.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/validate-process-forge-checksums.py --root . --check`
- `python tools/smoke_first_run.py`
- `python tools/smoke_resource_management.py`
- `git diff --check`

Next recommended action:
Review the MVP wording and decide whether true interactive prompts are needed before release.
