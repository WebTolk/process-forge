# Review remediation

The first independent review found two defects:

1. MCP callers could provide another project root after session lookup.
2. `POST /shutdown` bypassed the Runtime authorization check.

Both were corrected before the final proof:

- `mcp_server.py` now derives the bound project from Agent Ledger and rejects a
  supplied project root with a different `project_id`.
- `service.py` authorizes every POST route, including `/shutdown`.

The focused smoke validates both cases. The independent remediation review then
returned `PASS`; see
[ledger-hooks-mcp-next-stage-20260814-remediation-review.md](../../reviews/ledger-hooks-mcp-next-stage-20260814-remediation-review.md).
