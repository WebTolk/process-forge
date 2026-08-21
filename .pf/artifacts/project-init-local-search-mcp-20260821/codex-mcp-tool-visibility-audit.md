# codex-mcp-tool-visibility-audit

Source: accepted `project-initialization-contract.md` and official OpenAI documentation review.

The current stdio facade provides `pf.project_state`, `pf.work_state`, `pf.resolve`, `pf.workplace_state`, and the three Ledger-scoped session reads. It has no `pf.search`, initialization operation, or dynamic tool-list notification.

The implementation must keep a static MCP tool list. The official material reviewed documents tool-list retrieval for the Responses API, not confirmed Codex client handling of in-session `notifications/tools/list_changed`; therefore dynamic visibility is explicitly out of scope. A changed local MCP configuration requires client reconnect/restart and then a real `tools/list` verification.

Required live gates remain distinct: registry configured, snapshot activated, Codex sees the server, `tools/list` sees the tool, and a Ledger-bound session completes a safe call. Session mismatch, a missing session, or a foreign project assertion fail closed without diagnostic leakage.
