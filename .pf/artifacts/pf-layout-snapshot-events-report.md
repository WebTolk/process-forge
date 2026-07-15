# `.pf` Layout, Snapshot Events, Hooks, And Telemetry Report

## Status

implemented

## Scope

Implemented the stabilization layer for ProcessForge `.pf` project flow,
snapshot refresh/check, session telemetry, assignment capsules, structured
events, and hooks/webhook-ready outbox behavior.

This product repository still uses legacy root flow artifacts for dogfooding.
The current task did not move root flow directories into `.pf/`; migration stays
deferred pending review because root `docs/`, `schemas/`, `tools/`, `templates/`,
`processes/`, and `packages/` are product distribution source directories.

## Implemented

- `.pf/hooks.yaml` is generated for new projects.
- `project-context-refresh` writes project snapshot YAML/MD and private
  `runtime/cache/workplace-context.snapshot.yaml`.
- `project-context-check` now prints `STATUS`, `HEALTH`, and `RESULT`.
- Session start emits telemetry and structured flow events.
- Assignment capsule includes an event correlation id and emits assignment
  events.
- Event log writes NDJSON under `runtime/events/events.ndjson` for legacy root
  layout and `.pf/runtime/events/events.ndjson` for `.pf` projects.
- `hooks-dispatch` supports dry-run hook selection and outbox writes.
- Webhook/file-outbox hooks write private payloads under runtime outbox; the MVP
  does not send network requests or execute local commands.
- `context-resolve` and `context-compile` are explicitly deprecated compatibility
  commands with clear CLI messages.
- README and Getting Started now use the `.pf` + snapshot + telemetry + events
  path as the main model.

## Added

- `docs/concepts/processforge-events.md`
- `docs/concepts/hooks-and-webhooks.md`
- `schemas/processforge-event.schema.json`
- `schemas/hooks.schema.json`
- `templates/processforge-event-template.json`
- `templates/session-telemetry-event-template.json`
- `templates/hooks-template.yaml`
- `artifacts/pf-layout-snapshot-events-report.md`
- `reviews/pf-layout-snapshot-events-review.md`
- `handoffs/pf-layout-snapshot-events-handoff.md`

## Updated

- `tools/processforge.py`
- `tools/validate-process-forge-schemas.py`
- `tools/validate-public-cleanliness.py`
- `README.md`
- `docs/getting-started.md`
- `.gitignore`
- `.processforge-releaseignore`
- snapshot/session/front matter concept docs
- project init templates and generated project instructions

## Verification

Passed during implementation:

- `python -m py_compile tools\processforge.py tools\validate-process-forge-schemas.py tools\validate-public-cleanliness.py`
- `python tools\processforge.py project-context-refresh --project-root .`
- `python tools\processforge.py project-context-check --project-root .`
- `python tools\processforge.py context-resolve --project-root .`
- `python tools\processforge.py context-compile --project-root . --assignment задания\processforge_pf_layout_snapshot_events_master_prompt.md --capsule --supersede`
- `python tools\processforge.py hooks-dispatch --project-root . --event-type processforge.session.completed --dry-run`
- `python tools\validate-process-forge-schemas.py --root .`
- `python tools\validate-public-cleanliness.py --root .`
- `python tools\validate-process-forge-checksums.py --root .`
- `git diff --check` returned no whitespace errors; Git printed line-ending
  normalization warnings for modified text files.
- temporary `.pf` project smoke: init, hooks config creation, snapshot refresh/check, generated_at-only freshness check, assignment capsule, session-start telemetry/events, hook dry-run, and outbox creation.

## Known Warnings

- Current repository snapshot health remains `warn` because optional capability
  providers are unresolved.
- Current repository flow artifacts are still legacy root-layout. Migration
  remains documented but not performed.
- The assignment prompt has no YAML front matter, so the new automated
  `assignment-capsule` command treats it as human-readable only; a legacy ECP was
  generated for this repository's current boot sequence.

## Residual Risks

- Hook dispatch is intentionally MVP-level: no network sends and no local command
  execution.
- Event payload privacy depends on command authors keeping payloads sanitized.
- Full `.pf` dogfooding migration still needs a protected artifact inventory and
  review.
