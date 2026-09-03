# Telemetry Evidence Review

Result: `pass_with_conditions`.

## Confirmed

- Project event journal grew from 35 to more than 90 events and contains assignments, tasks, artifacts, worker runs, tool/MCP invocations and chat recording events.
- Worker input and expected report are captured as central raw events (`WorkerPromptPayloadSubmitted`, `WorkerExpectedReportCaptured`).
- Chat transcripts exist for implementation, review, manual hook acceptance and installed PF hook acceptance.
- Project context refresh produced durable telemetry files and refreshed search generations.
- Installed governed worker session `01a04d27-a5c5-7081-a15c-4ed9a238cb36` emitted native Codex hooks: 1 `SessionStart`, 1 `UserPromptSubmit`, 5 `PostToolUse`, 1 `SessionEnd`.
- The same session appears in Agent Ledger as check-in, five heartbeats and check-out.
- All eight project hooks point to the single installed PF `codex_hooks.py` entrypoint.
- Automatic hook trust is granted only for a complete PF-only hook file; a foreign handler disables it.

## Conditions And Limits

- `pf.search` returned no narrow Joomla content-plugin article. PF still provided authoritative knowledge paths and the exact Joomla 6.1.2 source tree, which the agents used first.
- PhpStorm MCP transport errors on port 64442 are external noise and do not affect PF MCP.
- The current interactive Codex app session predates the installed update; fresh Codex workers and the standalone MCP process load the installed code.

Conclusion: PF owns and persists the development process evidence required for this acceptance: control-plane calls, events, native hooks, chat, worker IO, ledger state, reports and context telemetry.
