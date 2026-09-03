# Codex Integration Audit

Status: pass with residual MCP schema gap

Current implementation:

- `tools/pf_runtime/codex_integration.py` manages project-local `.codex/hooks.json`.
- `project-onboard` installs managed hooks for new PF projects.
- `project-init-status` reports `codex_integration`.
- `project-init-repair --repair-action install_codex_hooks --apply` reinstalls missing/stale hooks.
- `.codex/hooks.json` is private local config and is protected by `.gitignore`.

Validated by:

- `python tools/smoke_codex_integration.py`
- `python tools/smoke_project_init_codex_integration.py`
- selected `release-test` for `smoke_project_init_codex_integration`

Residual: `tools/pf_runtime/mcp_server.py` schema was outside implementation
scope, so MCP repair schema does not yet advertise `install_codex_hooks`.
