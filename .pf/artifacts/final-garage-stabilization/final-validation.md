# Final Validation

Date: 2026-08-24
Result: pass_with_conditions

## Commands

```text
python -m py_compile src/processforge_core/garage.py tools/pf_runtime/mcp_server.py tools/pf_runtime/service.py tools/processforge.py tools/smoke_garage_mode_not_promoted_by_session.py tools/smoke_garage_work_start_sessionless.py tools/smoke_garage_work_start_session_bound.py tools/smoke_governed_work_stage_resolution.py tools/smoke_governed_work_duplicate_prevention.py tools/smoke_current_work_ignores_bootstrap_placeholder.py tools/smoke_derived_report_stale_marking.py tools/smoke_runtime_status_version_truth.py tools/smoke_user_like_garage_path.py tools/smoke_garage_session_enhanced.py
python tools/processforge.py release-test --root . --no-clean --only smoke_garage_mode_not_promoted_by_session --only smoke_garage_work_start_sessionless --only smoke_garage_work_start_session_bound --only smoke_governed_work_stage_resolution --only smoke_governed_work_duplicate_prevention --only smoke_current_work_ignores_bootstrap_placeholder --only smoke_derived_report_stale_marking --only smoke_runtime_status_version_truth --only smoke_user_like_garage_path --only smoke_garage_no_hooks_sessionless --only smoke_garage_session_enhanced --only smoke_garage_cross_project_security --only smoke_garage_real_joomla_search --only smoke_mcp_missing_session_diagnostics --only smoke_session_projection_expiry --only smoke_fulltext_article_indexing --only smoke_project_init_codex_integration --only smoke_doctor_gitignore_effective_protection
python tools/processforge.py doctor-project --project-root .
python tools/processforge.py events-validate --project-root .
python tools/processforge.py run-doctor --project-root . --run final-garage-stabilization-20260824
git diff --check
stdio MCP initialize + tools/list
```

Observed result: all commands passed. `doctor-project` still prints the known
warning that `.pf/runtime/bin/pf.py` is missing for a self-contained
distribution. `git diff --check` returned success and printed only CRLF working
copy warnings.

## Definition of Done Status

- Session does not promote Garage to Forge: pass.
- Garage mode follows project/runtime coordination: pass.
- Sessionless/session-bound `pf.context` returns same simple-project mode: pass.
- `pf.work.start` implemented: pass.
- `pf.work.start` selects/validates stage: pass.
- No manual run-create/task-create/stage guessing in user-like path: pass.
- Duplicate governed work prevention: pass.
- Bootstrap placeholder ignored as current substantive work: pass.
- Derived stale reports exposed to agents: pass_with_conditions.
- Runtime status separates installed PF and runtime instance: pass.
- Cross-project/security/privacy regressions: pass.
- Hosted MCP gap separated from stdio MCP acceptance: pass_with_conditions.

## Condition

Hosted Codex MCP visibility was not executed in this run. Local stdio
`tools/list` shows `pf.work.start`, and local smokes pass, but this is not a
hosted Codex acceptance claim.
