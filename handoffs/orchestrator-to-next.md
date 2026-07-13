# Handoff: Orchestrator -> Next Maintainer

Objective:
Continue ProcessForge after clean-start bootstrap.

Current status:
Bootstrap file-only product has been created. Validation should be rerun after any change.

Input artifacts:
- artifacts/bootstrap-scope.md
- artifacts/core-file-model.md
- artifacts/status-model.md
- artifacts/consolidated-roadmap.md
- reviews/bootstrap-review.md
- reviews/public-cleanliness-review.md

Files changed:
- See artifacts/changed-files.md.

Files not to touch:
- Do not edit approved artifacts without an upgrade or replacement note.
- Do not make runner or backend mandatory.

Known issues:
- Semantic validation is intentionally lightweight.
- Template usage records are not yet generated automatically.

Required checks:
- python tools/validate-process-forge-schemas.py
- python tools/validate-process-forge-checksums.py
- python tools/validate-public-cleanliness.py

Next recommended action:
Tighten validators and add adapter manifests for capability providers.
