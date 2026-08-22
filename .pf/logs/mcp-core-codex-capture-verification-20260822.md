## 2026-08-22 13:52 - codex-main

Task: Verify MCP, Python Core and Codex capture baseline.
Files changed: `.pf/artifacts/mcp-core-codex-capture-verification-20260822/baseline-verification.md`; this log.
Artifacts changed: baseline verification report.
Templates used: none.
Tools used: ProcessForge task/capsule commands; focused Python smoke tests; direct installed stdio MCP discovery; `codex mcp list`.
Decisions: Keep the existing beta qualification evidence intact. Treat missing project-local `.codex/hooks.json` as a configuration gap, not a Python Core defect.
Risks: Direct stdio MCP is proven, but a real Codex host tool call remains subject to host approval policy. No project-local Codex message is captured until hooks are installed.
Next steps: Create an isolated implementation task for project-local hook installation, then run a real hook-to-Ledger/chat-to-MCP verification.
Handoff: The baseline task may be completed after its report is registered.
