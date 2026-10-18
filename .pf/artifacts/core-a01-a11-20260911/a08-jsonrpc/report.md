# Primary fallback: A08

Author: primary orchestrator. Original Luna shell run failed backend 403 before
source edits; failure evidence remains under worker-failures/wave2/a08-jsonrpc.

Implemented JSON-RPC envelope and advertised tool-argument schema validation
before business dispatch. Invalid envelopes/params use distinct protocol errors;
malformed JSON recovers for subsequent requests. Valid notifications execute
without responses, including error paths; explicit null ids remain requests.

Primary verification PASS: smoke_mcp_jsonrpc_validation on real native stdio,
smoke_runtime_ledger_hooks_mcp and smoke_mcp_codex_contract. New regression fails
baseline. No new external dependency or installed-MCP change.

Changed: tools/pf_runtime/mcp_server.py, tools/smoke_mcp_jsonrpc_validation.py.
Independent source review is in progress under review-mcp-reports.
