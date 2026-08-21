# Codex hook registration audit

Status: adapter capability is present; release-visible registration is not confirmed.

## Observed implementation

`tools/pf_runtime/codex_hooks.py` accepts a native hook payload, writes it raw-first through Runtime or the durable Host/Core fallback, and normalizes only `SessionStart`, `SessionEnd`, and `PostToolUse`.

The same adapter accepts `UserPromptSubmit` raw-first and derives a user conversation message only when the prompt and source session id are present. It does not implement generic interactive assistant-response capture.

## Registration evidence

The repository has no `.codex/hooks.json`, and no release-visible generator or installation/configuration example for one was found. The project-local `.pf/hooks.yaml` configures ProcessForge outbox routing, not host Codex native-hook registration.

Product docs must distinguish adapter raw-capture capability, normalized mapping capability, current conversation mapping, and actual host registration. Do not advertise universal Codex-hook capture until a release-visible registration contract and live configuration evidence exist.
