# Kimi retest after device installation

The installed dev source is e4420e6a3b27480bcf0199a7a4ce4acc3eb1da1a; PF App Server was restarted and is ready. Actual installed-client HTTP delivery now passes against that server. Source/fixture QA is 92 tests and 13 subtests, plus Ruff/mypy. The real model run remains the next user check.

Start a fresh Kimi session and check automatic native session enrollment, two different prompt arrays, distinct native tool_call_id events, replay without duplicates, subagent response/agent_name and SessionEnd checkout. PostToolUseFailure is supported and verified synthetically. Existing Kimi host subscriptions and timeouts were preserved: earlier setup omitted that failure hook and used a 3-second timeout while PF transport allows 5 seconds. For full live failure-path coverage, include PostToolUseFailure and provide a sufficient hook timeout in Kimi configuration; no permission/yolo changes are needed for the adapter correction.

Stop/SessionEnd do not carry the main assistant answer in the inspected Kimi 2.3.0 contract, so capture of that unavailable text is not promised. Identical ID-less payloads remain indistinguishable from replay. Record native receipts and chat/event IDs separately from observer exit codes. Existing connected MCP processes predate this update; any fresh-host acceptance must be checked in the actual new session.
