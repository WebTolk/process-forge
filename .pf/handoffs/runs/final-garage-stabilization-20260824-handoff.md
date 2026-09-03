# Handoff: implementation -> maintainer

Objective:
Final Garage stabilization after Core Simplification.

Current status:
Completed with conditions. Local stdio MCP and release-test proof passed;
hosted Codex MCP visibility remains a follow-up.

Input artifacts:
.pf/artifacts/final-garage-stabilization/garage-forge-mode-semantics-audit.md
.pf/artifacts/final-garage-stabilization/governed-work-bootstrap-implementation-report.md
.pf/artifacts/final-garage-stabilization/user-like-garage-behavior-acceptance.md
.pf/artifacts/final-garage-stabilization/final-validation.md
.pf/runs/final-garage-stabilization-20260824/summary.md

Files changed:
src/processforge_core/garage.py
tools/pf_runtime/mcp_server.py
tools/pf_runtime/service.py
tools/processforge.py
docs/concepts/garage-core.md
docs/concepts/runtime-mcp.md
.pf/START_AGENT_HERE.md
tools/smoke_garage_mode_not_promoted_by_session.py
tools/smoke_garage_work_start_sessionless.py
tools/smoke_garage_work_start_session_bound.py
tools/smoke_governed_work_stage_resolution.py
tools/smoke_governed_work_duplicate_prevention.py
tools/smoke_current_work_ignores_bootstrap_placeholder.py
tools/smoke_derived_report_stale_marking.py
tools/smoke_runtime_status_version_truth.py
tools/smoke_user_like_garage_path.py

Files not to touch:
dist/**
.pf/runtime/**

Known issues:
Hosted Codex MCP acceptance was not run. Derived report lifecycle is exposed in
`pf.context.derived_reports`; legacy report producers were not fully migrated to
embed explicit snapshot metadata.

Required checks:
Repeat final Garage targeted release-test checks and run hosted Codex MCP tool
visibility acceptance from a fresh host session.

Next recommended action:
Verify hosted Codex MCP visibility and execute the preferred path from the host:
`pf.context -> pf.search -> pf.resolve -> pf.work.start`.
