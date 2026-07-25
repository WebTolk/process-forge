# Heartbeat Contract Fix Review

- reviewer: `codex`
- reviewed_at: `2026-07-25T14:36:25+04:00`
- result: `pass`

## Findings

- No `.ps1` files were added.
- No built-in Claude/Codex/Gemini/Cursor/OpenCode runtime drivers were added.
- Native subagent boundaries remain documented as external to PF runtime drivers.
- The heartbeat contract remains mandatory for shell-launched proof workers.
- Failed workers write heartbeat and `exit.json`, but `worker-run collect` still rejects failed status.
- The old targeted smoke now uses bounded polling and diagnostics rather than a direct `read_text()` on `heartbeat.json`.

## Risks

- The originally reported missing heartbeat did not reproduce against the current archive, so this change hardens confirmed contract gaps rather than proving the exact old failure path.
- Clean extracted release-test skips `git diff --check` because a ZIP extraction is not a Git checkout; archive validation still passed.
