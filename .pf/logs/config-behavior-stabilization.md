## 2026-07-26 12:05 - codex

Task:
Stabilize config-driven behavior from `задания/processforge_config_behavior_stabilization_master_prompt.md`.

Files changed:
`tools/processforge.py`, shell-agent smokes, shell-agent plan schema/template/example, docs, ADR, audit artifacts.

Artifacts changed:
`.pf/adr/config-driven-behavior-contract.md`, `.pf/artifacts/config-behavior-audit/inventory.yaml`, `.pf/artifacts/config-behavior-audit/report.md`, `.pf/artifacts/config-behavior-stabilization-report.md`, `.pf/reviews/config-behavior-stabilization-review.md`, `.pf/handoffs/config-behavior-stabilization-handoff.md`.

Templates used:
Project-local ProcessForge artifact conventions.

Tools used:
Serena search, PowerShell, `apply_patch`, Python smoke/validation commands.

Decisions:
`allow_write_scope_overlap: true` now materializes as an allow policy in assignments/capsules and supervisor scheduling. Unsupported public shell-agent plan fields fail validation unless in `metadata` or `x_`.

Risks:
Full release/archive validation still pending. Route status and continuation expected-artifact behavior remain partial MVP surfaces.

Next steps:
Run targeted smokes, validators, release-test, release-pack, release-archive-test, extracted archive checks, and `git diff --check`.

Handoff:
`.pf/handoffs/config-behavior-stabilization-handoff.md`.

## 2026-07-26 12:20 - codex

Task:
Finalize validation and release/archive proof for config behavior stabilization.

Files changed:
Checksum inventory and `dist/processforge.zip` / `dist/processforge.manifest.json` refreshed after public surface changes.

Artifacts changed:
`.pf/artifacts/config-behavior-audit/report.md`, `.pf/artifacts/config-behavior-stabilization-report.md`, `.pf/reviews/config-behavior-stabilization-review.md`, `.pf/handoffs/config-behavior-stabilization-handoff.md`.

Templates used:
ProcessForge release validation commands from the assignment.

Tools used:
PowerShell, `python bin/pf.py release-test`, `release-pack`, `release-archive-test`, archive hygiene check.

Decisions:
Keep the separate extracted archive proof even though `release-archive-test --extracted-test full` already passed, because the assignment requires targeted config smokes in a clean unpacked archive.

Risks:
Extracted archive cannot run git diff checks because it is not a git checkout; root `git diff --check` passed.

Next steps:
Review final diff and deliver summary.

Handoff:
No further handoff required unless a separate review/commit step is requested.
