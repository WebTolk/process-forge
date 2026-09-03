# External Audit Package Report

Status: passed — analysis-only handoff; not public-release approval.

## Deliverables

- Archive: `dist/processforge-1.1.0-external-audit-20260903.zip`
- Sidecar: `dist/processforge-1.1.0-external-audit-20260903.manifest.json`
- Size: 1,389,508 bytes
- SHA-256: `F4F619B4815FA391898130547F3AF01F2E993659FE207794A08C3B695259716A`
- Entries: 930
- Detached audit-candidate commit: `127173dfcb17dae1fcb06143577941fa87081b7d`
- Candidate tree: `12e9a0a4ff8e446ba5a696f9001e60ce7c46043d`

## Candidate boundary

The primary checkout was dirty and was not reset, committed, or used directly for `release-pack`. A detached clean candidate started at `ca8924e`, received only the audited multi-process Work Capsule source slice and `tools/smoke_multi_process_work_capsule.py`, regenerated its checksum inventory, and recorded a local detached audit commit. The output name is intentionally distinct from the existing public-looking 1.1.0 archives.

## Verification

- Candidate schema validation: PASS.
- Candidate checksum write and check: PASS.
- `release-pack`: PASS.
- Archive/sidecar hash, file-list, safe-member, and current-candidate parity checks: PASS.
- Required `src/processforge_core` and generated `processforge-core.manifest.json`: present.
- Forbidden `.pyc`, `__pycache__`, and `.pf/runtime` entries: 0.
- Quick extracted archive validation: PASS (84.45 s), including both launcher helps and its selected release-test checks.

The sidecar marks the deterministic clean candidate `release_eligible: true`; that packaging field is not a decision to publish. Full public requalification and the separate historical run-artifact-consistency gate remain outside this package.
