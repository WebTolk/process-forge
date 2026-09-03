# Fresh Git Project Acceptance

Generated: 2026-08-24 14:00 +04

## Fixture Coverage

Fresh temporary project coverage is provided by:

- `tools/smoke_project_init_codex_integration.py`;
- `tools/smoke_doctor_gitignore_effective_protection.py`;
- `tools/smoke_session_projection_expiry.py`;
- `tools/smoke_fulltext_article_indexing.py`.

The combined selected release-test run passed all five relevant smokes:

```text
python tools/processforge.py release-test --root . --only smoke_project_init_codex_integration --only smoke_doctor_gitignore_effective_protection --only smoke_mcp_missing_session_diagnostics --only smoke_session_projection_expiry --only smoke_fulltext_article_indexing --no-clean
RESULT: PASS
```

## What Is Proven

- Fresh onboarding installs project-local Codex hooks.
- Missing/stale hooks are repairable with `install_codex_hooks`.
- `.gitignore` effective protection for `.codex/hooks.json` is accepted.
- Expired Ledger presence updates current-session projections to `stale`.
- An authorized article fixture is indexed and searchable by unique fulltext.
- MCP missing-session failure carries actionable remediation metadata.

## Not Proven

- A new external Codex client process loading the hook file and emitting real
  SessionStart.
- Codex host MCP registry visibility for ProcessForge tools.

Status: `pass_with_conditions`.
