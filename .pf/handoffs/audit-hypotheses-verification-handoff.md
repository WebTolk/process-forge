# Handoff: Codex -> Release Owner

Objective:
Verify external audit hypotheses H1-H5 in the real local ProcessForge checkout,
fix only confirmed problems, retest, rebuild the canonical archive, and record
durable evidence.

Current status:
Pass. H1 was partially confirmed and fixed in the smoke. H4 was confirmed as
generated local state and handled with `clean --release`. H2, H3, and H5 were
not confirmed locally.

Input artifacts:
- `задания/processforge_verify_audit_hypotheses_fix_and_retest_master_prompt.md`
- `.pf/AGENTS.md`
- `.pf/process-forge.yaml`

Files changed:
- `tools/smoke_update_framework_validation.py`
- `.pf/artifacts/checksum-inventory.sha256`
- `.pf/artifacts/audit-hypotheses-verification-report.md`
- `.pf/reviews/audit-hypotheses-verification-review.md`
- `.pf/handoffs/audit-hypotheses-verification-handoff.md`
- `.pf/logs/task-log.md`
- `dist/processforge-v1.0.0.zip`
- `dist/processforge-v1.0.0.manifest.json`

Files not to touch:
- Previous release-sync artifacts unless the release owner asks for squashing or
  cleanup.
- Historical `.pf/*v0-1*` records.

Known issues:
- POSIX was not executed locally.
- Release tests can recreate `.pf/runtime`; run `python bin/pf.py clean --root .
  --release` before final packaging or before checking local generated-state
  cleanliness.

Required checks:
- `python tools/smoke_update_framework_validation.py`
- `python tools/smoke_update_framework_readonly.py`
- `python tools/smoke_multiagent_assignment_contract.py`
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
Review the combined working tree from the previous release-sync slice plus this
audit-hypothesis verification slice, then commit when accepted.
