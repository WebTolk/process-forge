# Garage/Forge Mode Semantics Audit

Date: 2026-08-24
Status: ready_for_implementation

## Findings

- `ProjectContextService.context()` currently sets `mode: forge` whenever a
  `session_id` is supplied.
- This contradicts the final Garage invariant: session enriches Garage; session
  does not promote Garage to Forge.
- The existing project/runtime coordination model already has the needed
  authority: `workplace_coordination.effective_mode` in the project snapshot and
  `effective_project_coordination()` in Core.
- Current checkout snapshot is `effective_mode: simple`, `director_required:
  false`; therefore `pf.context` must remain `mode: garage` with or without a
  bound session.
- Real Forge mode should follow organized/Director-required coordination, not
  mere session availability.

## Consumers

- MCP `pf.context` is the direct consumer.
- MCP `pf.work_state` currently derives its compact session/context payload from
  `ProjectContextService.context()`.
- Existing acceptance artifact
  `.pf/artifacts/garage-core-simplification/garage-session-enhanced-acceptance.md`
  recorded the old behavior and must be superseded by final acceptance.

## Minimal Fix

- Add `GarageModeService`.
- Compute mode from snapshot coordination:
  - `simple` or missing coordination -> `garage`;
  - `organized` or `director_required: true` -> `forge`.
- Always report session as a nested enrichment:
  - no session -> `session.status: absent`;
  - supplied valid session -> `session.status: bound`.
- If mode is `forge` and required runtime/Director infrastructure is not
  available, return an explicit diagnostic such as
  `forge_runtime_required_but_unavailable`.
