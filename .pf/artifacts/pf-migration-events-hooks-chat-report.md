# PF Migration Events Hooks Chat Report

## Status

ready_for_review

## Moved To `.pf/`

- `AGENTS.md` -> `.pf/AGENTS.md`
- `process-forge.yaml` -> `.pf/process-forge.yaml`
- `assignments/`, `artifacts/`, `contexts/`, `logs/`, `reviews/`, `handoffs/`, `adr/` -> `.pf/`
- `runtime/` -> `.pf/runtime/`
- `private-notes/` -> `.pf/private-notes/`

## Remained In Root

- `docs/`, `schemas/`, `tools/`, `processes/`, `packages/`, `templates/`, `examples/`
- `README.md`, `LICENSE`, `CHANGELOG.md`, `.gitignore`, `.processforge-releaseignore`

These are product distribution files or normal repository files. `.pf/process-forge.yaml` references root product seed packs through relative `../` paths.

## Event Taxonomy

Implemented process event categories include session, chat, process, stage, assignment, artifact, review, gate, tool, MCP, hook, context snapshot, and capability events.

Runtime events use a CloudEvents-inspired envelope with `event_id`, `event_type`, `source`, `subject`, `time`, correlation/causation ids, project/process/assignment/actor blocks, and `data`.

Schemas added or updated:

- `schemas/event-envelope.schema.json`
- `schemas/process-event.schema.json`
- `schemas/processforge-event.schema.json`
- `schemas/process-definition.schema.json`
- `schemas/assignment-front-matter.schema.json`

## Hook Dispatch

`.pf/hooks.yaml` is the project-level delivery config. Process definitions declare emitted and subscribed event points; hook config maps matching events to delivery targets.

Supported MVP behavior:

- `hooks-dispatch --dry-run`
- `hooks-dispatch --outbox`
- `--send` fails because network transport is future-only
- hook delivery result files under `.pf/runtime/hooks/results/`

## WTAICC Outbox Payload

WTAICC-bound payloads are written under:

```text
.pf/runtime/hooks/outbox/wtaicc/
```

Payload schema:

- `schemas/wtaicc-outbox-payload.schema.json`
- `target: wtaicc`
- `delivery_mode: outbox`
- embedded event envelope
- chat section with `metadata_only`, `redacted`, `full`, or `content_ref` mode

No network requests are sent by default.

## Chat Relay Privacy

Implemented MVP commands:

- `chat-record`
- `chat-export`

Transcript path:

```text
.pf/runtime/chat/transcripts/<session-id>.ndjson
```

Default event/outbox behavior is metadata-only. Content capture requires explicit `--include-content`; secret-like values are redacted before transcript/event/outbox serialization.

## Validation Results

- `python -m py_compile tools\processforge.py tools\validate-process-forge-schemas.py tools\validate-public-cleanliness.py tools\validate-process-forge-checksums.py`: pass
- `python tools\validate-process-forge-schemas.py --root .`: pass
- `python tools\validate-public-cleanliness.py --root .`: pass
- `python tools\validate-process-forge-checksums.py --root . --write`: pass
- `python tools\validate-process-forge-checksums.py --root . --check`: pass
- `python tools\processforge.py events-validate --project-root .`: pass
- `python tools\processforge.py project-context-check --project-root .`: pass with `HEALTH: warn`
- `python tools\processforge.py doctor-context --project-root .`: pass

Smoke checks completed:

- current dogfooding flow moved to `.pf/`
- project init creates `.pf/` only and no root `AGENTS.md`
- `project-context-refresh` emits events
- `session-start` emits session events and telemetry
- `assignment-capsule` emits events using an ignored runtime smoke assignment
- `doctor-context` emits a gate event
- `hooks-dispatch --dry-run` matches `wtaicc-outbox`
- `hooks-dispatch --outbox` writes WTAICC outbox payload and hook result
- `chat-record` writes transcript and emits `chat.message.recorded`
- `chat-export --outbox` writes WTAICC chat payload
- invalid event NDJSON is rejected
- invalid chat transcript NDJSON is rejected
- `.pf/runtime/` paths are ignored by git

## Remaining Risks

- `project-context-check` reports `HEALTH: warn` because optional capabilities remain unresolved; this does not block the current file-first flow.
- `context-resolve` and `context-compile` remain as deprecated compatibility commands; public docs no longer recommend them as the primary path.
- Network webhook delivery, command hook execution, process runner execution, and managed WTAICC transport are intentionally not implemented.
