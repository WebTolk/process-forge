# Handoff: release-test reliability fix -> release owner

Objective:
Make `python tools/processforge.py release-test --root .` complete reliably with PASS or explicit FAIL diagnostics, never a silent hang.

Current status:
Implemented and verified in both the working repository and a clean extracted release archive.

Input artifacts:
- `задания/processforge_release_test_reliability_fix_master_prompt.md`
- `.pf/artifacts/v0-1-release-hardening-report.md`
- `dist/processforge-v0.1.0.zip`
- `dist/processforge-v0.1.0.manifest.json`

Files changed:
- `bin/pf.py`
- `tools/processforge.py`
- `tools/smoke_first_run.py`
- `tools/smoke_resource_management.py`
- `docs/known-limitations.md`
- `docs/release-checklist.md`
- `docs/releases/v0.1.0.md`
- `.pf/artifacts/checksum-inventory.sha256`
- `dist/processforge-v0.1.0.zip`
- `dist/processforge-v0.1.0.manifest.json`
- reliability report/review/handoff artifacts

Files not to touch:
- Do not add Process Authoring MVP in this slice.
- Do not add daemon, watcher, runner, supervisor, orchestration, GUI, marketplace, remote sync, or publish automation.
- Keep `.pf/runtime/` and private/local state out of release archives.

Known issues:
- Windows launcher uses `os.spawnv(os.P_WAIT, ...)` fallback because `os.execv` was not reliable for argv/exit propagation in this environment.
- A manual diagnostic command created a test template under `C:\Temp`; removal was blocked by the execution policy. It is outside the repository and not part of release output.

Required checks:
- `python tools/processforge.py release-test --root .`
- `python tools/processforge.py release-pack --root . --output dist/processforge-v0.1.0.zip`
- `python tools/processforge.py release-archive-test --archive dist/processforge-v0.1.0.zip`
- `git diff --check`

Next recommended action:
Review and commit the combined v0.1 internal release candidate state when ready. Next product stage after acceptance is Process Authoring MVP.
