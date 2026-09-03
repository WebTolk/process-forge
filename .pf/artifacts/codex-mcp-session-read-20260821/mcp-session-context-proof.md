# MCP session context proof

`python tools/smoke_runtime_ledger_hooks_mcp.py` passed on 2026-08-21.

It starts two projects and Ledger sessions, calls `pf.session_context`, `pf.session_chat`, and `pf.session_activity`, and proves returned context is for `sess-a`. It also verifies no session returns exactly `{"error":{"code":"missing_session"}}`, while a second project's `project_root` returns exactly `{"error":{"code":"session_project_mismatch"}}`.
