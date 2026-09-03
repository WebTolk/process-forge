# Codex Exec Event Contract Audit

## Scope
- Assignment: `codex-exec-event-contract-audit-20260822`
- Evidence reviewed:
  - `.pf/artifacts/mcp-core-codex-capture-verification-20260822/live-capture-verification.md`
  - `tools/pf_runtime/codex_hooks.py`
  - `tools/pf_runtime/codex_integration.py`
  - `tools/smoke_codex_integration.py`
  - `docs/concepts/hooks-events.md`
  - `docs/concepts/codex-session-read.md`
  - `.codex/hooks.json`

## Contract definition
- Hook adapter supports events: `SessionStart`, `SessionEnd`, `PreCompact`, `PostCompact`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`.
- Normalized PF event mapping in `codex_hooks.py`:
  - `SessionStart` → `agent.session.started|resumed|clear|compact` (by `source`)
  - `SessionEnd` → `agent.session.ended`
  - `PreCompact` → `agent.session.compaction.started`
  - `PostCompact` → `agent.session.compacted`
  - `PostToolUse` → `agent.command.completed` (or `agent.tool.completed` when `tool_name` exists and is not `Bash`)
  - `UserPromptSubmit`, `Stop`, `SubagentStop` are treated as conversation-capable payloads in the envelope.
- Runtime contract for conversation payloads:
  - `UserPromptSubmit` writes derived user message if non-empty `prompt`.
  - `Stop` / `SubagentStop` write derived assistant message from non-empty `last_assistant_message`.
  - `Stop` and `SubagentStop` return `{}` in stdout as neutral, non-blocking protocol.
- `codex_integration.py` installer installs all above events and keeps changes limited to project `.codex/hooks.json`.
- Host MCP/session tooling is separate from hook registration (host trust and hook load must be confirmed independently via client inspection).

## Observed live-run compliance
- `.codex/hooks.json` contains all adapter-managed events and points to `tools/pf_runtime/codex_hooks.py` for each event group.
- `events-validate` in the live capture is **PASS**.
- Raw journal path includes native `SessionStart`, `UserPromptSubmit`, and `SessionEnd` records.
- Ledger/session activity appears to record derived lifecycle facts.
- `pf.session_context` and `pf.session_activity` paths are functioning in the observed run.

## Deviations / risks
- `pf.session_chat` in the live evidence returned **0 messages**, with no final assistant transcript in chat artifacts for that run.
- In this run, `Stop` did not appear as a captured event used to derive final assistant message, so the `Stop` conversation-capture branch did not execute.
- As a result, final assistant text capture is absent in this specific `codex exec` path despite the contract support.

## Verdict
- Adapter + installer contract implementation is **mostly compliant** and internally consistent.
- Live session-chat completeness in this `codex exec` sample is **partially non-conformant** (missing final assistant message derivation).

## Recommendation
1. Enforce a `codex exec` path that emits `Stop` (or explicit fallback event) with `last_assistant_message` for project-bound sessions.
2. Add explicit live verification assertions for each stage: raw native event, normalized ledger event, and chat derivation.
3. Continue to manage `.codex/hooks.json` via installer/remove tooling, and verify host `/hooks` trust state before depending on transcript completeness.