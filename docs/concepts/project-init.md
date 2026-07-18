# Project Init

Project Init connects one project to ProcessForge and to an already configured
workplace.

It answers:

```text
How does this project use ProcessForge on this workplace?
```

## Command Model

```bash
python bin/pf.py init-project --project-root <project-root> --workplace <workplace.yaml> --answers <answers.yaml> --dry-run
python bin/pf.py init-project --project-root <project-root> --workplace <workplace.yaml> --answers <answers.yaml> --apply
python bin/pf.py doctor-project --project-root <project-root>
```

## Modes

- `greenfield`: target project is empty or nearly empty.
- `brownfield`: target project already has files.

Brownfield mode never overwrites existing files without `--force`. If a
generated file conflicts, including `.gitignore`, the tool creates a
`.candidate` file or reports the conflict.

## Created Public Files

New projects use `.pf/` as the project flow root:

```text
.pf/AGENTS.md
.pf/process-forge.yaml
.pf/hooks.yaml
.pf/packages/project.<project-id>.yaml
.pf/artifacts/project-profile.md
.pf/artifacts/repository-map.md
.pf/artifacts/project-conventions.md
.pf/artifacts/toolchain-detection-report.md
.pf/artifacts/mcp-capability-report.md
.pf/artifacts/template-matching-report.md
.pf/artifacts/global-resource-matching-report.md
.pf/artifacts/project-init-proposal.md
.pf/reviews/project-init-review.md
```

Root project `AGENTS.md` is not created by default.

## Created Private Files

```text
.pf/process-forge.local.yaml
.pf/runtime/
.pf/cache/
.pf/private-notes/
```

The local file stores local paths and tool preferences. It must be listed in
`.gitignore`.

## Detection

Project Init scans only the project root supplied by the user. It detects
evidence such as `composer.json`, `package.json`, `phpunit.xml`, extension
manifests, workflow files, `docs/`, `content/`, `media/`, and existing source or
test directories.

All conclusions start as `observed`; they become `confirmed` only after review.
