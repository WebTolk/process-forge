# Handoff: intake-scope -> investigation

## Objective
Провести аудит предыдущей работы ProcessForge и проверить автоматическую запись хуков PF в outbox.

## Current status
- Intake-scope artifacts created: brief.md, scope.md, task-record.md, scope-accepted.md.
- Scope accepted; work moves to investigation.

## Input artifacts
- brief.md
- scope.md
- task-record.md
- scope-accepted.md

## Files changed
- None (audit mode).

## Files not to touch
- Product source code unless operator explicitly requests a fix.
- Historical PF-managed records (assignments, capsules, runs, logs).

## Known issues
- Outbox directory `.pf/runtime/hooks/outbox/wtaicc/` is empty.
- Need to determine whether PF is expected to write hooks automatically in current mode.

## Required checks
- Enumerate previous hook/audit related Work and their statuses.
- Inspect `.pf/hooks.yaml` effective configuration.
- Inspect hook delivery code path and smoke tests.
- Verify outbox state after controlled PF operations if safe.

## Next recommended action
Begin investigation by reading previous work artifacts and hook configuration.
