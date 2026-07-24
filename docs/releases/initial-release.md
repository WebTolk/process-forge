# Initial Release Notes

These notes describe the first file-first release line without naming a reusable
documentation version.

## Added

- Workplace/project first-run flow through `workplace-init`,
  `project-onboard`, and `agent-start-prompt`.
- Python-first CLI launchers with `bin/pf.py` as the canonical root launcher and
  `.pf/runtime/bin/pf.py` for linked projects.
- Resource authoring commands for reusable templates, knowledge packages, and
  platform contracts.
- Path constants and authoritative package roots for portable resource records.
- Project context snapshot refresh/check and assignment capsule generation.
- Runtime driver registry, worker-run lifecycle commands, and file-first process
  supervisor for bounded shell worker execution.
- Events/hooks/outbox MVP for file-only observational delivery.
- Release, smoke, examples, cleanup, package, and archive validation commands.

## Changed

- Public user commands prefer Python launchers.
- `START_AGENT_HERE` uses the local project Python launcher in linked projects.
- Release hygiene checks reject generated cache files, private paths,
  unsupported script wrappers, runtime payloads, local transcripts, and stale
  example data.
- Doctor commands include fix hints for the main first-run and
  resource-resolution failures.

## Known Limitations

- No claim or lease system for distributed coordination.
- Hooks are observational and outbox-only.
- No daemon, GUI, marketplace, remote sync, or publish service.
- No live command hook execution or network webhook send.

See [known limitations](../known-limitations.md).
