# Implementation report

2026-10-22. The Kimi Code 2.3.0 producer contract is implemented in kimi_hooks.py and kimi_adapters.py. Native tool_call_id preserves independent calls; ID-less canonical payload hashes preserve replay semantics. Prompt text parts and SubagentStop.response are captured with native agent_name. Stop/SessionEnd do not invent unavailable main-assistant text.

Ingress admission validates canonical derivation and actual receipts. HTTP rejection and malformed success receipts cannot trigger an offline policy bypass. Only transport unavailability uses the existing file ingress. Direct hook-script execution is supported. Hooks remain nonblocking observers, with diagnostic logging through the typed logger.

Seven historical capsules are restored to their pre-Kimi bytes in the Git index, without changing their live bytes or pins. The separate completed historical restoration restores the remaining 70 pre-existing files. Generic ingress, Codex behavior and installed configuration are unchanged by this source slice.

Synthetic native-shape fixtures and regression tests are in tests/kimi_hooks. Exact source hashes and tool commands are recorded in qa-verified.json. No source changes followed that successful qualification. The user's subsequent request authorizes a separate governed dev archive/device update after source delivery.
