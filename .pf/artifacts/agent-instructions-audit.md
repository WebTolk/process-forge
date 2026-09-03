# Agent Instructions Audit

Status: partial

Updated docs:

- `docs/concepts/project-init.md`
- `docs/validation/doctor-project.md`

The implemented contract is now documented:

1. `project-onboard` installs project-local Codex hooks.
2. `project-init-status` exposes `codex_integration`.
3. `project-init-repair --repair-action install_codex_hooks --apply` repairs hooks.
4. `.codex/hooks.json` is private local config.
5. `.gitignore` doctor accepts effective Git protection and warns on missing
   recommended exact entries.

Residual: global ProcessForge agent section and every EN/RU instruction surface
from the master prompt were not updated in this scoped slice.
