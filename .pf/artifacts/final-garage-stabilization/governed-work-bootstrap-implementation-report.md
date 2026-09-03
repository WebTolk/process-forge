# Governed Work Bootstrap Implementation Report

Date: 2026-08-24
Status: implemented

## Implemented

- Added `GarageModeService`: mode now follows project coordination, not session
  availability.
- Updated `ProjectContextService.context()`:
  - simple project without session -> `mode: garage`, `session.status: absent`;
  - simple project with bound session -> `mode: garage`, `session.status:
    bound`;
  - organized/Director-required project -> `mode: forge`;
  - missing Forge infrastructure -> diagnostic
    `forge_runtime_required_but_unavailable`.
- Added `CurrentWorkService`:
  - active substantive work excludes `first-assignment`;
  - duplicate active objective returns `continue_existing`;
  - completed historical duplicate returns `operator_choice_required`.
- Implemented real `GovernedWorkBootstrapService.start()` and MCP
  `pf.work.start`.
- Added `derived_reports` lifecycle markers in `pf.context`.
- Added explicit runtime status truth fields:
  - `installed_pf`;
  - `runtime`;
  - `last_runtime_instance`.

## Agent Contract

The preferred path is now:

```text
pf.context -> pf.search -> pf.resolve -> pf.work.start -> local work -> PF closeout
```

The agent provides objective/meaning. ProcessForge records run id, task id,
assignment id, stage, timestamps, session linkage, and gates.

## Tests Added

- `smoke_garage_mode_not_promoted_by_session`
- `smoke_garage_work_start_sessionless`
- `smoke_garage_work_start_session_bound`
- `smoke_governed_work_stage_resolution`
- `smoke_governed_work_duplicate_prevention`
- `smoke_current_work_ignores_bootstrap_placeholder`
- `smoke_derived_report_stale_marking`
- `smoke_runtime_status_version_truth`
- `smoke_user_like_garage_path`

All are registered in `release-test`.
