# Handoff: platform-agnostic-flow-cleanup -> release-validation

Objective:
Keep ProcessForge flow and core artifacts platform-agnostic while preserving
platform inheritance and resource authoring functionality.

Current status:
Implementation, checksum refresh, release-test, release-pack, and
release-archive-test are complete.

Input artifacts:
- `.pf/artifacts/platform-agnostic-flow-cleanup-report.md`
- `.pf/reviews/platform-agnostic-flow-cleanup-review.md`
- `tools/validate-public-cleanliness.py`
- `tools/smoke_platform_inheritance.py`

Files changed:
- `tools/`
- `templates/`
- `seeds/`
- `policies/`
- `examples/`
- `docs/`
- `.pf/artifacts/`
- `.pf/reviews/`
- `.pf/handoffs/`
- `.pf/logs/task-log.md`
- `dist/processforge-v0.1.0.zip`
- `dist/processforge-v0.1.0.manifest.json`

Known issues:
- None recorded.

Required checks:
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/validate-process-forge-checksums.py --root . --check`
- `python bin/pf.py release-test --root .`
- `python bin/pf.py release-archive-test --archive dist/processforge-v0.1.0.zip`
- `git diff --check`

Next recommended action:
Review the working tree and commit the completed platform-agnostic flow cleanup
slice when ready.
