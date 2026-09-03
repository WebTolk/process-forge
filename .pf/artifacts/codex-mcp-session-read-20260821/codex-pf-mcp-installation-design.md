# Codex PF MCP installation design

Codex host MCP configuration is distinct from PF workplace registry state. Install explicitly:

```powershell
codex mcp add processforge -- py -3 "D:\installed\processforge\tools\pf_runtime\mcp_server.py" --workplace "D:\processforge-workplace"
```

Verify host registration with `codex mcp list` and `/mcp`. The config is not automatically written by PF. Current Codex configuration documents static command/args/env but no per-turn session interpolation; `SessionStart` therefore supplies the Ledger session id as non-controlling additional context and calls pass it as `session_id`.
