# ProcessForge

ProcessForge is a file-first process system for governed repeatable workflows.
It turns process definitions, assignments, artifacts, reviews, handoffs, logs,
telemetry, events, hooks, and chat transcripts into durable context for AI
agents and humans.

ProcessForge does not require a backend, database, web UI, network transport, or
mandatory runner.

Current release candidate: `0.1.0-rc.1`.

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
- Runs live in `.pf/runs/<run-id>/run.yaml` and group assignment-backed tasks.
- Task iterations record repeated `work`, `debug`, `fix`, `review`, `test`,
  `research`, `handoff`, or `note` attempts inside `.pf/assignments/`.

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

Python CLI is the canonical runtime. `bin/pf.py` is the root launcher;
`bin/pf` and `bin/pf.bat` are thin optional wrappers over it.

```bash
python bin/pf.py workplace-init --workplace <workplace-root> --dry-run
python bin/pf.py workplace-init --workplace <workplace-root> --apply

python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic-software-project --dry-run
python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic-software-project --apply

python bin/pf.py agent-start-prompt --project-root <project-root>

python bin/pf.py project-context-refresh --project-root <project-root>
python bin/pf.py project-context-check --project-root <project-root>
python bin/pf.py session-start --mode resume --project-root <project-root> --report-only
python bin/pf.py assignment-capsule --project-root <project-root> --assignment .pf/assignments/example.md
```

Run a task batch:

```bash
python bin/pf.py run-create --project-root <project-root> --id <run-id> --title "<title>" --process task-batch-execution --apply
python bin/pf.py task-create --project-root <project-root> --run <run-id> --id task-001-example --title "Example task" --process software-feature-development --apply
python bin/pf.py iteration-add --project-root <project-root> --task task-001-example --kind work --summary "..." --apply
python bin/pf.py task-complete --project-root <project-root> --task task-001-example --summary "..." --apply
python bin/pf.py run-summary --project-root <project-root> --run <run-id> --apply
```

`init-workplace` and `init-project` remain compatibility commands. The first-run
UX uses `workplace-init` and `project-onboard` so workplace setup and project
onboarding stay separate.

Inside a normal linked project, use `pf doctor-project --project-root .` or
`python .pf/runtime/bin/pf.py doctor-project --project-root .`. Do not assume
that `tools/processforge.py` exists in the linked project root.

## Events, Hooks, And Chat

Events are written to `.pf/runtime/events/events.ndjson` with a portable
CloudEvents-inspired envelope.

Hook matching can be tested without writing payloads:

```bash
python bin/pf.py hooks-dispatch --project-root <project-root> --event-type session.ended --dry-run
```

Outbox delivery writes payloads under `.pf/runtime/hooks/outbox/`:

```bash
python bin/pf.py hooks-dispatch --project-root <project-root> --event-type assignment.completed --outbox
```

Chat capture writes local transcripts and emits `chat.message.recorded`:

```bash
python bin/pf.py chat-record --project-root <project-root> --session-id session-demo --participant operator --role user --content "Start the assignment"
python bin/pf.py chat-export --project-root <project-root> --session-id session-demo --target wtaicc --outbox
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
python bin/pf.py events-validate --project-root .
python bin/pf.py doctor-context --project-root .
python bin/pf.py release-test --root .
```

Release hygiene and packaging:

```bash
python bin/pf.py clean --root . --release
python bin/pf.py release-check --root .
python bin/pf.py release-pack --root . --output dist/processforge-v0.1.0.zip
```

See `docs/index.md`, `docs/getting-started.md`, `docs/concepts/`, and
`docs/known-limitations.md` for the detailed model.
