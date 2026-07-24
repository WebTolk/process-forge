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
