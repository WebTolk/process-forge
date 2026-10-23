# Native execution blocker

Three separate governed native PF contributors were prepared successfully and
started with the registered codex-exec driver and explicitly selected gpt-6.1-sol.
All three exited 1 before any READ_ACK, report or product edit. Native stderr shows
repeated HTTP 403 Forbidden from the Codex Responses WebSocket endpoint, alongside
model discovery timeout and unavailable optional MCP transports. These are actual
failed executions, not accepted contributions. Do not fabricate READ_ACK/RESULT.

Read-only checks: codex-cli 0.163.0 is installed; codex login status reports logged
in using ChatGPT. No credentials, driver/provider configuration, infrastructure,
account, Runtime or MCP service has been changed. A normal native retry of the
observation contribution is being observed separately; no limit/auth bypass used.

Exact prepared identities/receipts are retained in local control.private.json and
native runtime attempt files. The two new source owners and schedule owner do not
exist yet; all existing source modifications belong to the pre-existing baseline.
The user clarification is recorded in architecture-r2.md without mutating R1 pins.

Dependent implementation/review/release requires native CLI model access to work.
An authenticated local CLI status alone is not successful model execution. The
required operator action, if the ordinary retry also fails, is to restore working
Codex CLI access to the model/API for native PF workers. Do not publish alpha4 or
claim the task complete while its mandatory team/review and product QA are absent.

## Subsequent correction

The ordinary observation retry recovered inference and wrote partial observation
and access code. Its real READ_ACK/progress were in the managed usage-attempt-2
codex.jsonl receipt, not wrapper stdout/heartbeat. Primary stopped it too early.
The partial code is preserved and a normal third native attempt continues it.
The first three HTTP403 failures remain valid history; native model access is no
longer assumed blocked. Follow revision-handoff-r3.md and monitor actual receipts.
