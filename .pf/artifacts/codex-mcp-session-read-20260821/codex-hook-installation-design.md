# Codex hook installation design

Scope: opt-in project-local `<project>/.codex/hooks.json` only.

`codex_integration.py status|install|remove --project-root <path> [--apply]` loads the existing JSON, merges an exact managed Windows command handler for each observation event, and writes only with `--apply`. It copies the old file to a timestamped `.pf-backup-*` before atomic replacement. Removal matches that exact handler only, preserving unrelated operator handlers.

`install` is idempotent; status reports registration intent, not whether Codex has loaded/trusted the hook. The operator confirms the latter in `/hooks`. The installer does not edit shared `~/.codex` configuration or PF registry.
