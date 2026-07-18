# v0.1 Release Hardening Report

## Scope

ProcessForge was hardened to `0.1.0-rc.1` for the file-first single-agent release candidate. No runner, daemon, GUI, marketplace, remote sync, webhook send, or multi-agent claim/lease feature was added.

## Smoke Tests Stabilized

- `tools/smoke_resource_authoring_processes.py` now runs isolated scenarios instead of one shared temp chain.
- Every subprocess in that smoke uses a timeout.
- Timeout and unexpected-exit output includes command, cwd, expected/actual exit, and output tail.
- Positive full-chain, duplicate template, missing package root, missing required platform resources, optional platform resource warning, and no unsupported script-wrapper scenarios are separated.

## Release-Test

`python tools/processforge.py release-test --root .` runs:

- `py_compile`
- `clean --release`
- schema validation
- public cleanliness
- checksum validation
- `smoke_first_run.py`
- `smoke_resource_management.py`
- `smoke_resource_authoring_processes.py`
- `release-check`
- `examples-check`
- `events-validate`
- `doctor-project`
- `git diff --check`

Final observed result: `RESULT: PASS`.

## Release-Check

`release-check` validates the release surface for:

- required release files and directories;
- generated Python cache and bytecode;
- unsupported script wrappers;
- private local config and env files;
- runtime outbox/chat transcript paths;
- local/private absolute paths in user-facing public docs/examples/templates/processes/packages;
- obvious secret values in user-facing public files.

It prints `Why` and `Fix` hints for blocking failures.

## Release-Pack

`release-pack` builds `dist/processforge-v0.1.0.zip` and `dist/processforge-v0.1.0.manifest.json`.

Observed archive proof:

- required entries present: `README.md`, `QUICKSTART.md`, `CHANGELOG.md`, `LICENSE`, `AGENTS.md`, `bin/pf.py`, `bin/pf`, `bin/pf.bat`, `tools/processforge.py`, schemas, docs, examples;
- forbidden entries: `0`;
- manifest name: `processforge`;
- manifest version: `0.1.0`;
- manifest files: `258`.

## Docs Updated

- `README.md`
- `QUICKSTART.md`
- `CHANGELOG.md`
- `docs/index.md`
- `docs/known-limitations.md`
- `docs/releases/v0.1.0.md`
- linked-project command examples in getting-started, project onboarding, project init, doctor project, and first-run examples
- `docs/concepts/path-resolution.md` portable path examples

## Release Exclusions

The release surface excludes:

- `.pf/runtime/`
- `.pf/private-notes/`
- `.pf/cache/`
- generated cache directories and bytecode
- local IDE/tool state
- previous ZIP archives
- local transcripts and hook outbox payloads
- private local config
- task prompt folder `задания/`

## Known Limitations Fixed In Docs

`docs/known-limitations.md` records:

- file-only mode;
- no live AI session interception;
- observational/outbox-only hooks;
- no daemon/watch-events;
- no command hook execution;
- no multi-agent claim/lease;
- no runner/supervisor;
- no WTAICC integration;
- `--interactive` is a UX marker, not a terminal wizard;
- external documentation mirroring is plan/stub unless explicitly imported.

## Checks Passed

- `python -m py_compile tools/processforge.py tools/smoke_resource_authoring_processes.py tools/validate-process-forge-checksums.py tools/validate-public-cleanliness.py`
- `python tools/processforge.py clean --root . --release`
- `python tools/processforge.py examples-check --root .`
- `python tools/smoke_resource_authoring_processes.py`
- `python tools/processforge.py release-check --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/smoke_first_run.py`
- `python tools/smoke_resource_management.py`
- `python tools/processforge.py doctor-project --project-root .`
- `python tools/processforge.py events-validate --project-root .`
- `python tools/validate-process-forge-checksums.py --root . --write`
- `python tools/validate-process-forge-checksums.py --root . --check`
- `python tools/processforge.py release-pack --root . --output dist/processforge-v0.1.0.zip`
- `python tools/processforge.py release-test --root .`
- direct ZIP/manifest inspection

## Remaining After v0.1

- True interactive terminal prompting.
- Real runner/supervisor lifecycle.
- Daemon/watch-events.
- Command hook execution.
- Network webhook sending.
- Multi-agent claim/lease coordination.
- Remote package/index sync and publishing.
