# Handoff: platform-hardcode-cleanup -> release-validation

Objective:
Validate that ProcessForge platform inheritance, package dependencies, and
platform detection are data-driven and not hardcoded around Example Parent Platform or any other
domain.

Current status:
Implementation, docs, policies, seed manifests, smoke coverage, review, report,
release-test, release-pack, and release-archive-test are complete.

Input artifacts:
- `.pf/artifacts/platform-hardcode-cleanup-report.md`
- `.pf/reviews/platform-hardcode-cleanup-review.md`
- `tools/smoke_manifest_driven_platforms.py`
- `policies/core-hardcode-policy.yaml`

Files changed:
- `tools/processforge.py`
- `tools/smoke_platform_inheritance.py`
- `tools/smoke_manifest_driven_platforms.py`
- `tools/validate-process-forge-schemas.py`
- `policies/`
- `seeds/`
- EN/RU docs and public prompts describing manifest-driven platforms.
- `.pf/logs/task-log.md`

Files not to touch:
- `.pf/runtime/`
- Private local configs.

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
Review the working tree and commit the completed platform hardcode cleanup slice
when ready.
