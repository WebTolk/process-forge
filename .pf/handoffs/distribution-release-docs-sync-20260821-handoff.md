# Handoff: codex/run-coordinator -> release-sync implementer

Objective:
Synchronize the ProcessForge release archive, gates, checksums, public-cleanliness semantics, and built-in event/runtime documentation.

Current status:
Blocked at the clean-baseline gate. Audit evidence is complete; no product files were changed by this run.

Input artifacts:
- `.pf/artifacts/distribution-release-docs-sync-20260821/distribution-consistency-audit.md`
- `.pf/artifacts/distribution-release-docs-sync-20260821/public-cleanliness-false-positive-audit.md`
- `.pf/artifacts/distribution-release-docs-sync-20260821/codex-hook-registration-audit.md`
- `.pf/artifacts/distribution-release-docs-sync-20260821/event-docs-sync-audit.md`
- `.pf/artifacts/distribution-release-docs-sync-20260821/event-storage-scaling-risk.md`

Files changed:
- ProcessForge run/task/capsule records, audit artifacts, log, and this handoff.

Files not to touch:
- Existing dirty Central Event Ingress implementation and prior-run `.pf` files without an explicit scope handoff.

Known issues:
- checksum validation and public cleanliness fail;
- `release-pack` has no checksum/public-cleanliness preflight;
- direct/extracted archive proof is unavailable until clean Git provenance;
- docs still present an obsolete three-hook/project-only model.

Required checks:
- clean Git baseline before `release-pack`;
- source and extracted checksum/public-cleanliness checks;
- extracted `bin/pf.py --help` and `tools/processforge.py --help`;
- source/extracted Core, ingress, conversation, and replay smokes;
- docs link checks, `git diff --check`, independent release and documentation reviews.

Next recommended action:
Commit/push the pre-existing ingress baseline separately, then issue a scoped handoff for `tools/processforge.py`, `tools/validate-public-cleanliness.py`, checksums, and affected public documentation.
