# `.pf` Layout, Snapshot Events, Hooks, And Telemetry Review

## Reviewed Object

ProcessForge `.pf` layout, project context snapshot, telemetry, events, hooks,
and legacy command deprecation changes.

## Reviewer

ProcessForge self-review

## Result

pass_with_conditions

## Findings

- PASS: `.pf/` remains the default for new project flow.
- PASS: new projects get `.pf/AGENTS.md`, `.pf/process-forge.yaml`, and
  `.pf/hooks.yaml`.
- PASS: root project `AGENTS.md` is not created by default.
- PASS: snapshot refresh/check writes YAML/MD snapshot and private workplace
  snapshot.
- PASS: session-start and assignment-capsule emit telemetry/events.
- PASS: hook schema and hook dry-run/outbox behavior exist.
- PASS: context-resolve/context-compile are marked deprecated while remaining
  compatibility-safe.
- WARN: current product repository migration to `.pf/` is deferred.
- WARN: optional capability providers remain unresolved in the current snapshot.

## Required Follow-Up

- Decide whether to begin the dogfooding migration inventory.
- Add real provider health checks when tool/MCP registries carry executable
  provider metadata.
- Add a future explicit dispatcher if network webhooks or local command hooks are
  approved.

## Evidence

- `artifacts/pf-layout-snapshot-events-report.md`
- `docs/concepts/processforge-events.md`
- `docs/concepts/hooks-and-webhooks.md`
- `schemas/processforge-event.schema.json`
- `schemas/hooks.schema.json`
- `tools/processforge.py`

## Recommendation

Accept this stabilization stage with conditions and keep migration as a separate
reviewed task.
