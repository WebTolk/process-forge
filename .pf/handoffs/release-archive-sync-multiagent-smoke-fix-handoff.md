# Handoff: Codex -> Release Owner

Objective:
Synchronize the ProcessForge 1.0.0 release archive with current source, fix the
multiagent smoke portability issue, remove stale release artifacts, and record
dogfooding evidence.

Current status:
Pass. The canonical release archive is `dist/processforge-v1.0.0.zip` with
matching `dist/processforge-v1.0.0.manifest.json`.

Input artifacts:
- `задания/processforge_release_archive_sync_multiagent_smoke_fix_master_prompt.md`
- `.pf/AGENTS.md`
- `.pf/process-forge.yaml`

Files changed:
- `tools/processforge.py`
- `tools/smoke_multiagent_assignment_contract.py`
- `tools/smoke_update_framework_readonly.py`
- `docs/getting-started/agent-prompts.md`
- `docs/ru/getting-started/agent-prompts.md`
- `docs/release-checklist.md`
- `.pf/artifacts/checksum-inventory.sha256`
- `.pf/artifacts/release-archive-sync-multiagent-smoke-fix-report.md`
- `.pf/reviews/release-archive-sync-multiagent-smoke-fix-review.md`
- `.pf/handoffs/release-archive-sync-multiagent-smoke-fix-handoff.md`
- `.pf/logs/task-log.md`
- `dist/processforge-v1.0.0.zip`
- `dist/processforge-v1.0.0.manifest.json`

Files removed:
- `dist/processforge-v0.1.0.zip`
- `dist/processforge-v0.1.0.manifest.json`
- tracked `.pf/runtime/` skeleton files

Files not to touch:
- Existing historical `.pf/artifacts/*v0-1*` and `.pf/handoffs/*v0-1*`
  records unless a separate cleanup assignment is opened.

Known issues:
- POSIX was not executed locally. The smoke fixture itself no longer has a
  case-only dependency.
- `doctor-project` reports warnings for optional onboarding skeleton files after
  `.pf/runtime/` cleanup, but `release-test` passes.

Required checks:
- `python tools/smoke_multiagent_assignment_contract.py`
- `python tools/smoke_update_framework_readonly.py`
- `python tools/smoke_update_framework_validation.py`
- `python tools/smoke_manifest_driven_platforms.py`
- `python tools/smoke_platform_inheritance.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/validate-process-forge-checksums.py --root . --check`
- `python bin/pf.py release-test --root .`
- `python bin/pf.py release-pack --root . --output dist/processforge-v1.0.0.zip`
- `python bin/pf.py release-archive-test --archive dist/processforge-v1.0.0.zip`
- `git diff --check`

Next recommended action:
Review the final git diff and commit the release archive sync slice if the
tracked `.pf/runtime/` deletion is accepted as the intended public cleanup.
