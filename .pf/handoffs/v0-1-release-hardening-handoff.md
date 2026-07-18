# Handoff: v0.1 release hardening -> release owner

Objective:
Stabilize ProcessForge as `0.1.0-rc.1` for the file-first single-agent release candidate.

Current status:
Release hardening is implemented and locally verified.

Input artifacts:
- `задания/processforge_v0_1_release_hardening_master_prompt.md`
- `.pf/AGENTS.md`
- `.pf/process-forge.yaml`

Files changed:
- `tools/processforge.py`
- `tools/smoke_resource_authoring_processes.py`
- `tools/validate-process-forge-checksums.py`
- `tools/validate-public-cleanliness.py`
- `README.md`
- `QUICKSTART.md`
- `CHANGELOG.md`
- `VERSION`
- `docs/`
- `examples/first-run/`
- `.pf/process-forge.yaml`
- `.pf/contexts/project-context.snapshot.*`
- `.pf/artifacts/checksum-inventory.sha256`
- `dist/processforge-v0.1.0.zip`
- `dist/processforge-v0.1.0.manifest.json`

Files not to touch:
- No runtime/private user data should be added to the release archive.
- Do not widen this slice into runner, daemon, multi-agent lease, GUI, marketplace, remote sync, or publish automation work.

Known issues:
- `doctor-project` WARN entries are expected for this repository's self-contained dogfooding mode.
- `dist/` is local generated release output; decide separately whether to commit, publish, or regenerate it in CI.

Required checks:
- `python tools/processforge.py release-test --root .`
- inspect `dist/processforge-v0.1.0.zip` and `dist/processforge-v0.1.0.manifest.json`
- `git diff --check`

Next recommended action:
Review the diff and decide the commit/publish boundary for the `0.1.0-rc.1` release candidate.
