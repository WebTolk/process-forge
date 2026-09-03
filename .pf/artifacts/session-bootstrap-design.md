# Session Bootstrap Design

Status: partial

Implemented path:

```text
Codex SessionStart
-> project-local .codex/hooks.json
-> tools/pf_runtime/codex_hooks.py
-> Runtime /event when available
-> Host/Core durable raw ingress fallback when Runtime is unavailable
-> Ledger-bound session id from provider payload
```

The adapter does not invent a second PF session id. It uses the provider
session id and can return a non-controlling `SessionStart` additional context.

Residual: proving a fresh real Codex SessionStart requires starting a new Codex
session after hooks are installed. The current already-running session cannot
retroactively prove that event.
