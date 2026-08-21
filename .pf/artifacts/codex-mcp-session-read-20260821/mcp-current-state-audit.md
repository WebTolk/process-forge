# MCP current-state audit

Date: 2026-08-21

- Baseline MCP was stdio/read-only with `pf.project_state`, `pf.work_state`, `pf.resolve`, and `pf.workplace_state` in `tools/pf_runtime/mcp_server.py`.
- It already routed `--session`/`PF_MCP_SESSION_ID` through Agent Ledger, but returned exception text and had no bounded session/chat/activity models.
- Transcript storage is private per session under `.pf/runtime/chat/transcripts`; project events store chat metadata, not message content.
- Raw Codex input goes through `RawIngressKernel`; raw workplace payloads are neither MCP data nor release content.

Result: add the three session read tools in a shared Runtime read layer and do not introduce a separate MCP-to-project binding.
