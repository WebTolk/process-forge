## 2026-07-29 14:41 - codex

Task:
Execute `задания/processforge_specialization_project_overrides_master_prompt.md`.

Files changed:
- `tools/processforge.py`
- `tools/validate-process-forge-schemas.py`
- `schemas/`
- `templates/`
- `docs/`
- `tools/specialization_smoke_helpers.py`
- new specialization/project override smokes
- `.pf/artifacts/specialization-and-project-overrides-report.md`
- `.pf/reviews/specialization-and-project-overrides-review.md`
- `.pf/handoffs/specialization-and-project-overrides-handoff.md`

Artifacts changed:
- Added implementation report, review request, handoff, and this log.

Templates used:
- `.pf/AGENTS.md` logging/handoff format.

Tools used:
- Serena project memory and configuration
- PowerShell fallback for file/context reads
- `apply_patch`
- targeted Python smokes

Decisions:
- Implemented specializations as workplace/project resources with registry and
  project-local override support.
- Kept runtime resolution generic and fixture-only in public smokes.
- Treated hard-required resource disable as conflict; project disable applies to
  recommended/optional resources.

Risks:
- `overlay`, `replace`, and `fork` are recorded but not fully deep-merged in MVP.
- No release validation blocker remains for this slice.

Next steps:
- Review final diff.
- Commit/push only on explicit request.

Handoff:
- `.pf/handoffs/specialization-and-project-overrides-handoff.md`

## 2026-07-29 15:02 +04:00 - codex

Task:
Finalize validation after public-cleanliness fixture fixes.

Files changed:
- `tools/processforge.py`
- `tools/specialization_smoke_helpers.py`
- `tools/smoke_specialization_platform_binding.py`
- `tools/smoke_specialization_no_core_id_hardcode.py`
- `tools/smoke_project_overrides_capsule_summary.py`
- `tools/smoke_specialization_capsule_activation.py`
- `checksums/processforge.sha256`
- `.pf/artifacts/specialization-and-project-overrides-report.md`
- `.pf/reviews/specialization-and-project-overrides-review.md`
- `.pf/handoffs/specialization-and-project-overrides-handoff.md`
- `.pf/logs/specialization-and-project-overrides.md`

Status:
Validated.

Checks:
- New specialization/project override smoke set: PASS.
- `validate-process-forge-schemas.py --root .`: PASS.
- `validate-public-cleanliness.py --root .`: PASS.
- `validate-process-forge-checksums.py --root . --check`: PASS.
- `bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1 --trace-smokes`: PASS.
- `bin/pf.py release-pack --root . --output dist/processforge.zip`: PASS, 722 files.
- `bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1`: PASS.
- `git diff --check`: PASS.

Residual risks:
- `overlay`, `replace`, and `fork` remain recorded/schema-supported MVP modes,
  without arbitrary deep merge behavior in the resolver.
