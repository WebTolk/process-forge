# Handoff: config-behavior-stabilization

Objective:
Stabilize config-driven behavior for shell-agent plans, overlap policy, subagent policy, supervisor scheduling, and release smokes.

Current status:
Implementation, focused smoke checks, full public release-test, packaging, archive validation, clean extracted archive proof, and archive hygiene checks are complete.

Input artifacts:
- `задания/processforge_config_behavior_stabilization_master_prompt.md`
- `.pf/artifacts/config-behavior-audit/inventory.yaml`
- `.pf/artifacts/config-behavior-audit/report.md`
- `.pf/adr/config-driven-behavior-contract.md`

Files changed:
- `tools/processforge.py`
- `tools/smoke_config_behavior_contracts.py`
- `tools/smoke_orchestrator_shell_agents_with_subagent_policy.py`
- `schemas/orchestrator-shell-agent-plan.schema.json`
- `templates/orchestrator-shell-agent-plan.yaml`
- `examples/orchestrator-shell-agents/minimal/orchestrator-shell-agent-plan.yaml`
- docs and `.pf` closeout artifacts

Files not to touch:
- `.pf/runtime/`
- `.pf/dogfooding/`
- unrelated release/package files unless validation requires checksum/archive refresh

Known issues:
- Route status and continuation expected artifact behavior remain partial MVP surfaces.
- Extracted archive release-test reports `git diff --check skipped: not a git repo`, which is expected for the temporary unpacked archive. Root `git diff --check` passed.

Required checks:
- `python tools/smoke_config_behavior_contracts.py`
- `python tools/smoke_orchestrator_shell_agents_with_subagent_policy.py`
- `python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1`
- `python bin/pf.py release-pack --root . --output dist/processforge.zip`
- `python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1`

Next recommended action:
Package this slice for review or commit/push if requested.
