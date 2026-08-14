# Runtime Model

![Run lifecycle](../assets/processforge-run-lifecycle.svg)

ProcessForge uses short-lived CLI commands by default. A command reads project
and workplace files, writes the requested artifact or runtime record, emits
events under `.pf/runtime/`, and exits.

The file layout is the runtime contract:

- `.pf/process-forge.yaml` stores the project manifest.
- `.pf/contexts/` stores refreshed context snapshots.
- `.pf/runs/` stores run records.
- `.pf/assignments/` stores task and iteration records.
- `.pf/artifacts/`, `.pf/reviews/`, and `.pf/handoffs/` store evidence and
  delivery material.
- `.pf/runtime/events/events.ndjson` stores event envelopes.
- `.pf/runtime/agent-runs/` stores optional worker process state.
- `.pf/runtime/supervisor/` stores optional supervisor loop state.

The optional future watcher or runner can observe these files, but the core
runtime does not require a daemon.

Runtime drivers and the process supervisor are optional runtime helpers. See
[Runtime drivers](runtime-drivers.md) and
[Process supervisor](process-supervisor.md).

## Distribution Root Versus Linked Project

From the distribution root, run:

```bash
python bin/pf.py release-test --root .
```

Inside a linked project, run:

```bash
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

## Runtime Requirements

Runtime usage expects Python 3.11+ recommended, Python 3.10+ only when the current tests confirm compatibility, Python package dependencies from `requirements.txt` including `PyYAML`, a UTF-8 capable filesystem, and read/write access to the ProcessForge distribution, workplace, and project folders.

Runtime usage does not require PowerShell, Git, a daemon, or a background process. Git is only needed when the user wants version-control integration or when development/release checks are being run.
# Runtime, Ledger, and read-only interfaces

PF Runtime is a workplace-scoped local lifecycle host, scheduler, and IPC
transport. It is not a second PF Core. Agent Ledger owns agent/session
presence and the canonical session-to-project binding; Runtime's project and
session maps are rebuildable caches only.

A routed session is recovered from the Ledger record's `project_id` and
`project_root`. A request or event that names a different project is rejected.
This keeps recovery after Runtime-cache removal and cross-project isolation
independent of the daemon.

Codex hooks are thin fact adapters. They normalize documented lifecycle or tool
facts, append existing PF events, and delegate check-in, heartbeat, and
checkout to Core. The stdio MCP facade is read-only and exposes
`pf.project_state`, `pf.work_state`, `pf.resolve`, and `pf.workplace_state` for
an already Ledger-bound session.

## Declaration-driven technical projections

Process definitions may declare a stage `technical_obligations` entry. The
Runtime Host reads that declaration and writes only a separate generated file
under `.pf/artifacts/projections/`; it does not contain stage business rules or
edit semantic reports, handoffs, or output bodies.

The first projector, `required-output-readiness`, is bound to the
`process-supervisor` `collect` stage. It derives the current stage obligation
from the assignment, Inspector worker state, and required-output fingerprints.
Its view is `current`, `stale`, `missing`, or `invalid`. It can be rebuilt with
`runtime-host rebuild-projections` and verified without a daemon using
`runtime-host projection-doctor`.
