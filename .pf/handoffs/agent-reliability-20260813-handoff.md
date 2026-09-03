# Handoff: codex-main -> implementation

Objective:
Implement the approved first slice from the agent reliability audit.

Current status:
Audit/design is complete; product code is unchanged. The current project
context remains broken after refresh, so capsule generation is blocked.

Input artifacts:
- `.pf/artifacts/agent-reliability-20260813/audit-report.md`
- `.pf/assignments/audit-and-architecture.yaml`
- `задания/process-forge-agent-reliability-master-prompt.md`

Files changed:
- `.pf` run/task/log/audit artifacts for current work.
- `.pf/contexts/project-context.snapshot.*` refreshed by CLI.

Files not to touch:
- Product files until the operator approves the implementation slice.

Known issues:
- `run-summary` overwrites rich handoff content.
- Run/task/event writes do not share a transaction/lock primitive.
- `session-status-report.md` can be stale and still look current.
- Context refresh/check currently reports broken state after refresh.

Required checks:
- `python tools/processforge.py project-context-check --project-root .`
- `python tools/processforge.py events-validate --project-root .`
- targeted new smokes for handoff preservation, stale session-status, atomic task-create, old damaged events history
- public release-test after implementation and checksum refresh

Next recommended action:
Ask operator to approve Phase 1: safe writes and handoff protection.
