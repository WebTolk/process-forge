# Handoff: final-pre-release-refinements -> release-validation

Objective:
Validate the final pre-release refinements slice and package it for release.

Current status:
Implementation, docs, examples, smoke coverage, dogfooding report/review, release-test, release-pack, and release-archive-test are complete.

Input artifacts:
- `.pf/artifacts/final-pre-release-refinements-report.md`
- `.pf/reviews/final-pre-release-refinements-review.md`
- `tools/smoke_platform_inheritance.py`

Files changed:
- `tools/processforge.py`
- `tools/smoke_platform_inheritance.py`
- `tools/validate-process-forge-schemas.py`
- `schemas/platform-contract.schema.json`
- `schemas/process-forge-manifest.schema.json`
- `schemas/project-context-snapshot.schema.json`
- EN/RU docs and examples listed in the report.

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
Review the working tree and commit the completed pre-release refinement slice when ready.
