## 2026-08-22 13:56 - codex-main

Task: Install project-local Codex observation hooks.
Files changed: `.codex/hooks.json` (ignored local configuration); `.gitignore`; `.pf/artifacts/mcp-core-codex-capture-verification-20260822/hook-installation-report.md`; this log.
Artifacts changed: hook installation report.
Templates used: none.
Tools used: ProcessForge task/capsule commands; `codex_integration.py`; integration smoke; Git ignore check.
Decisions: Use the explicit opt-in installer and keep its machine-local adapter configuration untracked.
Risks: Registration does not by itself prove host event ordering or transcript capture. A fresh Codex execution has already exposed an ordering failure that is recorded in the succeeding assurance task.
Next steps: Reproduce the event-order race under a dedicated assurance task and decide remediation from evidence.
Handoff: Installation is complete and idempotent; do not commit `.codex/hooks.json`.
