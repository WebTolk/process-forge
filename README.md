# ProcessForge

ProcessForge is a file-first process system for governed repeatable workflows.
It turns process definitions, assignments, artifacts, reviews, handoffs, logs,
telemetry, events, hooks, and chat transcripts into durable context for AI
agents and humans.

ProcessForge does not require a backend, database, web UI, network transport, or
mandatory runner.

## Core Model

- The project flow root is `.pf/`.
- `.pf/AGENTS.md` is the project flow entrypoint.
- `.pf/process-forge.yaml` is the project-local manifest.
- Product distribution files can remain at repository root.
- Project context is refreshed into `.pf/contexts/project-context.snapshot.*`.
- Runtime telemetry, events, hooks, outbox payloads, and chat transcripts stay
  under `.pf/runtime/` and are ignored by git.
- Process definitions declare which events matter.
- `.pf/hooks.yaml` declares where matching events are delivered.
- Chat relay is opt-in and metadata-only by default for outbox payloads.

## Repository Layout

```text
project/
  docs/                      # product documentation
  schemas/                   # public schemas
  tools/                     # CLI and validators
  processes/                 # seed process packs
  packages/                  # seed package manifests
  templates/                 # seed templates
  examples/                  # public examples
  .pf/                       # project flow state
    AGENTS.md
    process-forge.yaml
    hooks.yaml
    contexts/
    assignments/
    artifacts/
    logs/
    handoffs/
    reviews/
    adr/
    runtime/
      events/events.ndjson
      hooks/outbox/wtaicc/
      hooks/results/
      chat/transcripts/
```

Root project `AGENTS.md` is not created by default.

## Quick Start

```bash
python tools/processforge.py init-workplace --root <workplace-root> --dry-run
python tools/processforge.py init-workplace --root <workplace-root> --apply

python tools/processforge.py init-project --project-root <project-root> --workplace <workplace.yaml> --dry-run
python tools/processforge.py init-project --project-root <project-root> --workplace <workplace.yaml> --apply

python tools/processforge.py project-context-refresh --project-root <project-root>
python tools/processforge.py project-context-check --project-root <project-root>
python tools/processforge.py session-start --mode resume --project-root <project-root> --report-only
python tools/processforge.py assignment-capsule --project-root <project-root> --assignment .pf/assignments/example.md
```

## Events, Hooks, And Chat

Events are written to `.pf/runtime/events/events.ndjson` with a portable
CloudEvents-inspired envelope.

Hook matching can be tested without writing payloads:

```bash
python tools/processforge.py hooks-dispatch --project-root <project-root> --event-type session.ended --dry-run
```

Outbox delivery writes payloads under `.pf/runtime/hooks/outbox/`:

```bash
python tools/processforge.py hooks-dispatch --project-root <project-root> --event-type assignment.completed --outbox
```

Chat capture writes local transcripts and emits `chat.message.recorded`:

```bash
python tools/processforge.py chat-record --project-root <project-root> --session-id session-demo --participant operator --role user --content "Start the assignment"
python tools/processforge.py chat-export --project-root <project-root> --session-id session-demo --target wtaicc --outbox
```

The MVP does not send network webhooks or execute local commands.

## Legacy Compatibility

`context-resolve` and `context-compile` remain deprecated compatibility commands.
They write into `.pf/contexts/`; new flows should use `project-context-refresh`,
`project-context-check`, and `assignment-capsule`.

## Validation

```bash
python tools/validate-process-forge-schemas.py
python tools/validate-process-forge-checksums.py
python tools/validate-public-cleanliness.py
python tools/processforge.py events-validate --project-root .
python tools/processforge.py doctor-context --project-root .
```

See `docs/getting-started.md` and `docs/concepts/` for the detailed model.
