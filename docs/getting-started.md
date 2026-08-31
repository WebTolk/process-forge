# Getting Started

ProcessForge starts with files, not services. A project flow lives under `.pf/`.
Python CLI is the canonical runtime.

## Garage and Forge

| | Garage | Forge |
|---|---|---|
| Runtime daemon | Not required | Required when coordination uses it |
| MCP | Host-owned stdio process | Host-owned stdio process |
| Ledger session | Not needed for `pf.context/search/resolve/work.start` | Used for orchestration |
| Hooks | Optional telemetry | Optional host-specific telemetry |
| Director | No | Yes when required by coordination |
| Runtime autostart | Not needed | Recommended/required |

The normal project-agent path is `pf.context -> pf.search -> pf.resolve ->
pf.work.start`. Current context outranks historical generated reports. Runtime,
MCP, hook, Ledger, and index maintenance are operator/advanced paths.

## Initialize A Workplace

```bash
python bin/pf.py workplace-init --workplace <workplace-root> --dry-run
python bin/pf.py workplace-init --workplace <workplace-root> --apply
python bin/pf.py doctor-workplace --root <workplace-root>
```

## Initialize A Project

```bash
python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic-software-project --dry-run
python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic-software-project --apply
python bin/pf.py doctor-project --project-root <project-root>
python bin/pf.py agent-start-prompt --project-root <project-root>
```

Project onboarding creates `.pf/AGENTS.md`, `.pf/START_AGENT_HERE.md`,
`.pf/process-forge.yaml`, `.pf/process-forge.local.yaml`, `.pf/hooks.yaml`,
`.pf/assignments/first-assignment.yaml`, `.pf/runtime/bin/pf.py`, context
snapshot files, onboarding artifacts, and the project flow folders. It does not create root project
`AGENTS.md` by default and does not recreate the workplace.

Inside a linked project, run:

```bash
pf doctor-project --project-root .
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

If a command needs a flow root and `.pf/process-forge.yaml` is missing, it should
tell the operator to run `project-onboard --project-root <project-root>
--workplace <workplace-root> --type <project-type> --apply` instead of creating
root-layout files. `init-project` is a compatibility command name.

## Refresh Project Context

```bash
python bin/pf.py project-context-refresh --project-root <project-root>
python bin/pf.py project-context-check --project-root <project-root>
```

The refresh command writes:

```text
.pf/contexts/project-context.snapshot.yaml
.pf/contexts/project-context.snapshot.md
.pf/runtime/cache/workplace-context.snapshot.yaml
```

## Advanced: Start A Ledger Session

```bash
python bin/pf.py session-start --mode resume --project-root <project-root> --report-only
```

This is a Forge/operator diagnostic path. Garage does not require a manual
session. Session start reads the snapshot, reports freshness, writes private
telemetry, and emits events under `.pf/runtime/`.

## Advanced: Run An Assignment Directly

Assignments use YAML front matter or assignment YAML for machine-readable
metadata. Markdown body text is human-readable context.

```bash
python bin/pf.py assignment-capsule --project-root <project-root> --assignment .pf/assignments/example.md
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
python bin/pf.py hooks-dispatch --project-root <project-root> --event-type session.ended --dry-run
```

Outbox delivery writes private payloads under `.pf/runtime/hooks/outbox/`:

```bash
python bin/pf.py hooks-dispatch --project-root <project-root> --event-type assignment.completed --outbox
```

Network send is disabled in the MVP.

## Chat Relay

Chat transcript capture is local and opt-in:

```bash
python bin/pf.py chat-record --project-root <project-root> --session-id session-demo --participant operator --role user --content "Start"
python bin/pf.py chat-export --project-root <project-root> --session-id session-demo --target wtaicc --outbox
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
python bin/pf.py events-validate --project-root .
python bin/pf.py doctor-context --project-root .
python bin/pf.py release-test --root .
```

`context-resolve` and `context-compile` are compatibility-only commands. New
project instructions should use `.pf/`, project context snapshots, session
telemetry, assignment capsules, process events, hooks, and chat relay.
