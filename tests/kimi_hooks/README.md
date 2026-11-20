# Kimi Code native hook contract

Portable fixtures reconstruct the payload shapes emitted by
`@moonshot-ai/kimi-code` 2.3.0. They contain synthetic text and a placeholder
project path, not captured conversations, credentials or machine details.
Source inspected: bundled `packages/agent-core-v2/src/features/externalHooks/`
regions `internal/matchHooks.ts`, `agent/agentExternalHooksService.ts` and
`session/sessionExternalHooksService.ts`.

The producer converts top-level camelCase to snake_case. Tool hooks use
`tool_call_id`; user prompts contain content parts; `SubagentStop` carries
`agent_name` and its response summary. `Stop` and `SessionEnd` do not supply
the main assistant's answer. Non-text parts remain raw-only. An ID-less hook
with an identical payload cannot be distinguished from its replay; its
canonical payload hash intentionally has one derived effect.

Tests exercise canonical mapping, distinct calls, exact replay, private text
capture, first-hook enrollment, forged-provenance denial, real receipt handling
and the direct hook-script entry point. They do not start PF infrastructure or
call a real Kimi model.
