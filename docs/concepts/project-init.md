# Project Init

Project Init connects one project to ProcessForge and to an already configured
workplace.

It answers:

```text
How does this project use ProcessForge on this workplace?
```

## Command Model

For dry-run, `<project-root>` must already exist because the command inspects
the target directory. Apply mode can create a missing greenfield project root.

```bash
python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic-software-project --dry-run
python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic-software-project --apply
python bin/pf.py project-init-status --project-root <project-root>
python bin/pf.py doctor-project --project-root <project-root>
python bin/pf.py agent-start-prompt --project-root <project-root>
```

`init-project` remains a compatibility command name. Public docs should prefer
`project-onboard` because it makes the existing-workplace boundary explicit.

## Modes

- `greenfield`: target project is empty or nearly empty.
- `brownfield`: target project already has files.

Brownfield mode never overwrites existing files without `--force`. If a
generated file conflicts, including `.gitignore`, the tool creates a
`.candidate` file or reports the conflict.

## Created Public Files

New projects use `.pf/` as the project flow root. `build_project_files()` and
`project_runtime_launcher_files()` currently write:

```text
AGENTS.md
.pf/AGENTS.md
.pf/agent-entry.json
.pf/process-forge.yaml
.pf/hooks.yaml
.pf/assignments/first-assignment.yaml
.pf/packages/project.<project-id>.yaml
.pf/artifacts/project-profile.md
.pf/artifacts/project-classification-report.md
.pf/artifacts/repository-map.md
.pf/artifacts/project-conventions.md
.pf/artifacts/toolchain-detection-report.md
.pf/artifacts/mcp-capability-report.md
.pf/artifacts/template-matching-report.md
.pf/artifacts/global-resource-matching-report.md
.pf/artifacts/project-init-proposal.md
.pf/artifacts/project-onboarding-report.md
.pf/reviews/project-init-review.md
.pf/reviews/project-onboarding-review.md
.pf/handoffs/project-ready-handoff.md
```

Onboarding also refreshes the context snapshot under `.pf/contexts/`, writes
the launcher under `.pf/runtime/bin/` and initializes the SQL journals and
execution store for a fresh project. [Execution storage](execution-storage.md)

Root `AGENTS.md` and hidden `.pf/AGENTS.md` receive the same minimum contract K.
The root is the ordinary entry; hidden extended instructions are read on demand.
Entry ownership and budget checks cannot be bypassed with `--force`.
`first-assignment.yaml` remains a compatibility placeholder, not required Work.
`agent-start-prompt` is a no-write preview; START is no longer needed or generated.
Existing START files are preserved. Missing START does not affect readiness or
doctor, and deterministic repair does not restore it. Explicit compatibility
placement remains separate.
See [entry migration and legacy status](agent-entry.md).

## Created Private Files

```text
.pf/process-forge.local.yaml
.pf/runtime/bin/pf.py
```

The local file stores local paths and tool preferences. `.gitignore` is updated
so `.codex/hooks.json`, `.pf/process-forge.local.yaml`, `.pf/runtime/`,
`.pf/private-notes/`, and `.pf/cache/` are ignored. Cache and private-notes are
reserved/ignored project areas, not normal onboarding output payloads.

### Example of native hook setup

The linked workplace’s default project mode determines hook setup. With
`organized`, a preview reports the planned Codex changes. Apply merges eight
handlers into the project’s `.codex/hooks.json` and backs up an existing file
before replacement. Status includes missing or stale required handlers in
the initialization repair plan. A conflict or unavailable required adapter
can block readiness. On a Garage workplace the same integration is optional.
The operator can select `project-init-repair --repair-action install_codex_hooks
--apply`. The client controls trust and activation. [Forge hook setup](../guides/forge-init-hooks.md)

## Detection

Project Init scans only the project root supplied by the user. It detects
evidence such as `composer.json`, `package.json`, `phpunit.xml`, extension
manifests, workflow files, `docs/`, `content/`, `media/`, and existing source or
test directories.

All conclusions start as `observed`; they become `confirmed` only after review.
