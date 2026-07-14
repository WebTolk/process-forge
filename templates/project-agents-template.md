# ProcessForge Project Instructions

This project uses ProcessForge.

## Start Order

1. Read `.pf/process-forge.yaml`.
2. Read `.pf/contexts/project-context.snapshot.md`.
3. If the snapshot is missing or stale, run/request project context refresh.
4. Read the current assignment from `.pf/assignments/` if assigned.
5. Read latest `.pf/artifacts/session-status-report.md` if present.
6. Read latest relevant logs/reviews/handoffs.
7. Use only tools/templates listed in snapshot or assignment.
8. Write session telemetry to `.pf/runtime/telemetry/`.

## Important Rules

- Do not edit files outside assignment scope.
- Do not put absolute local paths into public files.
- Do not commit `.pf/process-forge.local.yaml`.
- Do not commit `.pf/runtime/`.
- Use project-local templates before global templates when allowed.
- Record template usage.
- Record tool/MCP usage in session telemetry.
