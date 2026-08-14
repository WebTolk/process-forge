# Live validation: Codex lifecycle hook, Runtime, Ledger, and MCP

Date: 2026-08-14 (UTC)

## Live Codex driver and hook

`codex exec` was run in `D:\Dev\process-forge` with model
`gpt-5.3-codex-spark`, read-only sandbox, and the documented one-run
`--dangerously-bypass-hook-trust` switch. This was necessary only for the live
test because Codex requires a review/trust decision for non-managed command
hooks.

The project-local `.codex/hooks.json` invoked
`tools/pf_runtime/codex_hooks.py`. The Codex trace reported:

- `hook: SessionStart Completed`
- `hook: PostToolUse Completed`
- worker response `HOOK_LIVE_OK`

The durable Agent Ledger grew from 5 to 8 records for session
`019ffea8-ceb0-7913-8e10-5e3570ee7a62`: `agent.checked_in`,
`agent.heartbeat`, and `agent.checked_out`. The Runtime operator journal
records the corresponding authenticated `POST /event` calls at 05:05:20Z,
05:05:28Z, and 05:05:32Z. This proves daemon ingress rather than only the
adapter's Ledger fallback.

## Live MCP read

The stdio MCP server was called with that Ledger session. `pf.project_state`
returned project `process-forge`, and `pf.resolve` returned the same bound
project and workplace. The focused smoke separately proves rejection of a
cross-project MCP request and a `401` response for unauthenticated
`POST /shutdown`.

## Runtime lifecycle

The Runtime was started for `D:\.agents\processforge-workplace`, responded to
`/readyz` and authenticated `/status`, then stopped via its authenticated
`/shutdown` path. No daemon was left running after the test.

## Regressions

- `python -m py_compile ...` — PASS
- `python tools/smoke_runtime_ledger_hooks_mcp.py` — PASS
- `python tools/smoke_long_lived_runtime.py` — PASS
- `python tools/validate-process-forge-schemas.py --root .` — PASS
- `python tools/validate-public-cleanliness.py --root .` — PASS
- `git diff --check` — PASS (only CRLF notices)
