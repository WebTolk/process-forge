# Getting Started

ProcessForge starts with files, not services. A project flow lives under `.pf/`.

## Initialize A Workplace

```bash
python tools/processforge.py init-workplace --root <workplace-root> --dry-run
python tools/processforge.py init-workplace --root <workplace-root> --apply
python tools/processforge.py doctor-workplace --root <workplace-root>
```

## Initialize A Project

```bash
python tools/processforge.py init-project --project-root <project-root> --workplace <workplace.yaml> --dry-run
python tools/processforge.py init-project --project-root <project-root> --workplace <workplace.yaml> --apply
python tools/processforge.py doctor-project --project-root <project-root>
```

Project init creates `.pf/AGENTS.md`, `.pf/process-forge.yaml`,
`.pf/process-forge.local.yaml`, `.pf/hooks.yaml`, and the project flow folders.
It does not create root project `AGENTS.md` by default.

If a command needs a flow root and `.pf/process-forge.yaml` is missing, it tells
the operator to run `init-project` instead of creating root-layout files.

## Refresh Project Context

```bash
python tools/processforge.py project-context-refresh --project-root <project-root>
python tools/processforge.py project-context-check --project-root <project-root>
```

The refresh command writes:

```text
.pf/contexts/project-context.snapshot.yaml
.pf/contexts/project-context.snapshot.md
.pf/runtime/cache/workplace-context.snapshot.yaml
```

## Start A Session

```bash
python tools/processforge.py session-start --mode resume --project-root <project-root> --report-only
```

Session start reads the snapshot, reports freshness, writes private telemetry,
and emits `session.started` / `session.ended` events under `.pf/runtime/`.

## Run An Assignment

Assignments use YAML front matter or assignment YAML for machine-readable
metadata. Markdown body text is human-readable context.

```bash
python tools/processforge.py assignment-capsule --project-root <project-root> --assignment .pf/assignments/example.md
```

The capsule is written to `.pf/contexts/assignment-capsules/` and includes the
snapshot checksum, assignment scope, capabilities, required outputs, telemetry
path, and event correlation id.

## Events And Hooks

Core commands emit events to:

```text
.pf/runtime/events/events.ndjson
```

Hook matching can be tested without sending or writing payloads:

```bash
python tools/processforge.py hooks-dispatch --project-root <project-root> --event-type session.ended --dry-run
```

Outbox delivery writes private payloads under `.pf/runtime/hooks/outbox/`:

```bash
python tools/processforge.py hooks-dispatch --project-root <project-root> --event-type assignment.completed --outbox
```

Network send is disabled in the MVP.

## Chat Relay

Chat transcript capture is local and opt-in:

```bash
python tools/processforge.py chat-record --project-root <project-root> --session-id session-demo --participant operator --role user --content "Start"
python tools/processforge.py chat-export --project-root <project-root> --session-id session-demo --target wtaicc --outbox
```

`chat-record` writes `.pf/runtime/chat/transcripts/<session-id>.ndjson` and
emits `chat.message.recorded`. By default, exported payloads include metadata,
hashes, and local content references; full redacted content requires
`--include-content`.

## Validation

Run:

```bash
python tools/validate-process-forge-schemas.py
python tools/validate-process-forge-checksums.py
python tools/validate-public-cleanliness.py
python tools/processforge.py events-validate --project-root .
python tools/processforge.py doctor-context --project-root .
```

`context-resolve` and `context-compile` are compatibility-only commands. New
project instructions should use `.pf/`, project context snapshots, session
telemetry, assignment capsules, process events, hooks, and chat relay.
