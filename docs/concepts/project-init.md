# Project Init

Project Init connects one project to ProcessForge and to an already configured
workplace.

It answers:

```text
How does this project use ProcessForge on this workplace?
```

## Command Model

```bash
python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic-software-project --dry-run
python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic-software-project --apply
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
.pf/AGENTS.md
.pf/START_AGENT_HERE.md
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

The onboarding command also refreshes the project context snapshot under
`.pf/contexts/` and writes runtime launcher files under `.pf/runtime/bin/`.

Root project `AGENTS.md` is not created by default.

## Created Private Files

```text
.pf/process-forge.local.yaml
.pf/runtime/bin/pf.py
```

The local file stores local paths and tool preferences. `.gitignore` is updated
so `.pf/process-forge.local.yaml`, `.pf/runtime/`, `.pf/private-notes/`, and
`.pf/cache/` are ignored. Cache and private-notes are reserved/ignored project
areas, not normal onboarding output payloads.

## Detection

Project Init scans only the project root supplied by the user. It detects
evidence such as `composer.json`, `package.json`, `phpunit.xml`, extension
manifests, workflow files, `docs/`, `content/`, `media/`, and existing source or
test directories.

All conclusions start as `observed`; they become `confirmed` only after review.
