# Live Codex Proof

Run: `operational-hardening-search-update-20260822`

## Status

Not executed in this local slice.

## Reason

The available environment can run the stdio MCP smoke and local CLI/runtime tests, but it cannot prove the host UI trust state for `/hooks`, `/mcp`, or Codex approval policy from inside the repository alone.

## Evidence Available

`tools/smoke_project_init_local_search_mcp.py` verifies stdio MCP initialize, tools/list, `pf.session_context`, and `pf.search` against a controlled Ledger session.
