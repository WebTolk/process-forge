# Hook Recovery Plan

## Status

Automatic outbox recording works; no recovery is required for process-event hooks.

## Recommended actions

1. **Live Kimi Code hook verification**
   - Start a Ledger-bound Kimi Code session (operator action).
   - Send `SessionStart` and `PostToolUse` payloads to `tools/pf_runtime/kimi_hooks.py`.
   - Verify delivery in `.pf/runtime/hooks/outbox/wtaicc/` and `.pf/runtime/hooks/results/`.

2. **Diagnose previous audit failure**
   - Create a separate Work for `full-current-pf-audit-static-executor-20261014`.
   - Investigate `unknown_exit` in worker runtime.

3. **Outbox maintenance policy**
   - Planning-only Work to define rotation/cleanup for `.pf/runtime/hooks/outbox/`.
   - Current volume: 140k+ files; risk of disk exhaustion.

4. **Session telemetry**
   - Follow workplace AGENTS.md rule: write session telemetry when working inside ProcessForge.
