# Domain Notes

## Core concepts

- **Native hook / event**: lifecycle fact delivered by host (Kimi Code / Codex) to PF adapter.
- **Normalized PF event**: provider-neutral event recorded in project event journal.
- **Outbox payload**: file-first hook delivery artifact under `.pf/runtime/hooks/outbox/`.
- **Work transition**: stage change that emits `process.stage.*` events and triggers hook dispatch.

## Actors

- Host agent (Kimi Code CLI) — emits lifecycle hooks.
- PF adapter (`kimi_hooks.py` / `codex_hooks.py`) — normalizes and delivers to Runtime/Core.
- ProcessEventRecorder — persists events and dispatches outbox hooks.
- RuntimeHookDispatcher — writes outbox payloads and delivery results.

## Rules

- File-first mode: no daemon required for outbox writing.
- Network send is disabled by default; outbox is the persistent delivery channel.
- Approved artifacts and capsules are immutable; audit work must not rewrite history.
