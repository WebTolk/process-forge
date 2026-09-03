# Final Validation: After-New-Project Stabilization

Generated: 2026-08-24 14:00 +04

## Passed

```text
python -m py_compile tools/processforge.py tools/pf_runtime/mcp_server.py tools/smoke_mcp_missing_session_diagnostics.py tools/smoke_session_projection_expiry.py tools/smoke_fulltext_article_indexing.py
python tools/smoke_mcp_missing_session_diagnostics.py
python tools/smoke_fulltext_article_indexing.py
python tools/smoke_session_projection_expiry.py
python tools/smoke_project_init_codex_integration.py
python tools/smoke_doctor_gitignore_effective_protection.py
python tools/processforge.py release-test --root . --only smoke_project_init_codex_integration --only smoke_doctor_gitignore_effective_protection --only smoke_mcp_missing_session_diagnostics --only smoke_session_projection_expiry --only smoke_fulltext_article_indexing --no-clean
python tools/processforge.py project-context-check --project-root .
python tools/processforge.py doctor-project --project-root .
python tools/processforge.py events-validate --project-root .
git diff --check
```

## Conditions

- `doctor-project` emitted an existing warning:
  `.pf/runtime/bin/pf.py missing for self-contained ProcessForge distribution`.
- `git diff --check` emitted only CRLF replacement warnings.
- Fresh real Codex SessionStart and Codex MCP host visibility were not provable
  inside the current already-running worker.

Status: `pass_with_conditions`.
