# Garage Clean Project Acceptance

Status: partial pass

Validated by:

- `python tools/smoke_project_init_codex_integration.py`
- `python tools/smoke_project_init_acceptance.py`

Confirmed:

- a new PF project receives `.codex/hooks.json`;
- `project-init-status` reports Codex hooks installed;
- missing hooks become `repairable`;
- `project-init-repair --repair-action install_codex_hooks --apply` reinstalls them;
- project initialization, repair, FTS lifecycle, and session obligation
  acceptance still pass.

Not proven in this running session:

- fresh real Codex SessionStart captured after restarting Codex from the new
  target project.
