# Handoff: base-technologies-as-knowledge-packages -> release-validation

Objective:
Validate the follow-up slice that models base languages and web technologies as
knowledge packages and capabilities rather than platform contracts.

Current status:
Implementation, docs, examples, smoke coverage, review artifact, combined
two-task report, release-test, release-pack, and release-archive-test are
complete.

Input artifacts:
- `.pf/artifacts/base-technologies-as-knowledge-packages-report.md`
- `.pf/reviews/base-technologies-as-knowledge-packages-review.md`
- `.pf/artifacts/final-pre-release-two-task-summary.md`
- `tools/smoke_platform_inheritance.py`

Files changed:
- `tools/processforge.py`
- `tools/smoke_platform_inheritance.py`
- `tools/validate-process-forge-schemas.py`
- `templates/platform-contract-example-parent.yaml`
- EN/RU README, quickstart, concept docs, authoring docs, and examples listed in
  the report.

Files not to touch:
- `.pf/runtime/`
- Private local configs.

Known issues:
- None recorded for this slice.

Required checks:
- `python tools/smoke_platform_inheritance.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/validate-process-forge-checksums.py --root . --check`
- `python bin/pf.py release-test --root .`
- `python bin/pf.py release-pack --root . --output dist/processforge-v0.1.0.zip`
- `python bin/pf.py release-archive-test --archive dist/processforge-v0.1.0.zip`
- `git diff --check`

Next recommended action:
Review the working tree and commit the completed two-task pre-release slice when
ready.
