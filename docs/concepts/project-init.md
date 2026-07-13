# Project Init

Project Init connects one project to ProcessForge and to an already configured workplace.

It answers:

```text
How does this project use ProcessForge on this workplace?
```

## Command Model

Future CLI:

```bash
processforge init project
processforge doctor project
```

MVP script equivalent:

```bash
python tools/processforge.py init-project --project-root <project-root> --workplace <workplace.yaml> --answers <answers.yaml> --dry-run
python tools/processforge.py init-project --project-root <project-root> --workplace <workplace.yaml> --answers <answers.yaml> --apply
python tools/processforge.py doctor-project --project-root <project-root>
```

## Modes

- `greenfield`: target project is empty or nearly empty.
- `brownfield`: target project already has files.

Brownfield mode never overwrites existing files without `--force`. If a generated file conflicts, including `.gitignore`, the tool creates a `.candidate` file or reports the conflict.

## Created Public Files

```text
AGENTS.md
process-forge.yaml
packages/project.<project-id>.yaml
artifacts/project-profile.md
artifacts/repository-map.md
artifacts/project-conventions.md
artifacts/toolchain-detection-report.md
artifacts/mcp-capability-report.md
artifacts/template-matching-report.md
artifacts/global-resource-matching-report.md
artifacts/project-init-proposal.md
reviews/project-init-review.md
```

## Created Private Files

```text
process-forge.local.yaml
```

The local file stores absolute paths and local tool preferences. It must be listed in `.gitignore`.

## Detection

Project Init scans only the project root supplied by the user. It detects evidence such as `composer.json`, `package.json`, `phpunit.xml`, Joomla-style extension manifests, `.github/workflows`, `docs/`, `content/`, `media/`, and existing source/test directories.

All conclusions start as `observed`; they become `confirmed` only after review.
