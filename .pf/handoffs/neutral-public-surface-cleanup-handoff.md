# Handoff: neutral-public-surface-cleanup -> release-validation

Objective:
Validate that the v0.1 public surface is neutral and that real ecosystems
discussed during design are not accidentally shipped as support packs.

Current status:
Implementation, release-test, release-pack, and release-archive-test are
complete.

Input artifacts:
- `.pf/artifacts/neutral-public-surface-cleanup-report.md`
- `.pf/reviews/neutral-public-surface-cleanup-review.md`
- `policies/public-support-policy.yaml`
- `tools/smoke_manifest_driven_platforms.py`

Files changed:
- `tools/processforge.py`
- `tools/smoke_manifest_driven_platforms.py`
- `tools/smoke_platform_inheritance.py`
- `tools/smoke_process_authoring.py`
- `tools/smoke_authoring_parity.py`
- `tools/validate-process-forge-schemas.py`
- `policies/public-support-policy.yaml`
- `seeds/`
- `examples/`
- `docs/`
- `templates/`
- `.pf/logs/task-log.md`

Known issues:
- None recorded for this slice.

Required checks:
- `python tools/smoke_manifest_driven_platforms.py`
- `python tools/smoke_platform_inheritance.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/validate-process-forge-checksums.py --root . --check`
- `python bin/pf.py release-test --root .`
- `python bin/pf.py release-pack --root . --output dist/processforge-v0.1.0.zip`
- `python bin/pf.py release-archive-test --archive dist/processforge-v0.1.0.zip`
- `git diff --check`

Next recommended action:
Review the working tree and commit the completed neutral public surface cleanup
slice when ready.
