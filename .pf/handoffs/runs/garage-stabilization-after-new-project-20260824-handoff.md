# Handoff: codex -> next-agent

Objective:
Continue Garage stabilization after scoped after-new-project fixes.

Current status:
Implementation and local acceptance passed with conditions.

Input artifacts:
- `.pf/artifacts/garage-after-new-project-stabilization-current-state-audit.md`
- `.pf/artifacts/stabilization-implementation-report-after-new-project.md`
- `.pf/artifacts/final-validation-after-new-project.md`
- `.pf/artifacts/garage-stabilization-combined-report-20260824.md`

Files changed:
- `tools/pf_runtime/mcp_server.py`
- `tools/processforge.py`
- `tools/smoke_mcp_missing_session_diagnostics.py`
- `tools/smoke_session_projection_expiry.py`
- `tools/smoke_fulltext_article_indexing.py`
- `docs/concepts/runtime-mcp.md`
- `docs/concepts/resource-search-index.md`

Files not to touch:
- Do not rewrite historical approved artifacts unless a new assignment grants
  scope and marks them superseded.

Known issues:
- Fresh real Codex SessionStart is not proven.
- Codex MCP host registration/tool visibility is not proven.
- Runtime version labels still use PoC constants.
- Governed work bootstrap is design-only.

Required checks:
- Open a new Codex host session and verify hook ingress.
- Verify ProcessForge MCP visibility from Codex host.
- Run Ledger-bound `pf.search` through real MCP.

Next recommended action:
Create a host-level acceptance run after restarting/opening Codex with the
project-local `.codex/hooks.json` installed.
