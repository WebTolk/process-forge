# Codex MCP registration proof

Status: partially verified; successful search execution is blocked by the
Codex CLI approval policy.

The local stdio server was registered globally under the non-secret name
`processforge`. `codex mcp get processforge --json` and `codex mcp list`
report it as enabled.

A new read-only `codex exec` session was instructed to use only
`processforge/pf.search` with an explicit Ledger session id. The live CLI
reported:

```text
mcp: processforge/pf.search started
mcp: processforge/pf.search (failed)
MCP tool call requires approval, but approval policy is never
```

This proves Codex registry visibility and Codex-first tool selection. It does
not prove a completed search result: the configured approval policy refuses
the tool invocation. No dangerous approval/sandbox bypass was used.

Required next action for a fully successful live gate: run the same
non-mutating `pf.search` call in a Codex session that permits this MCP tool,
then record the returned `search_status` and result provenance.
