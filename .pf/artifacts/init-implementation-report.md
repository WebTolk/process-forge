# Init Implementation Report

## Status

reviewed_for_mvp

## Scope

Implemented ProcessForge Init MVP for:

- workplace initialization
- project initialization
- workplace doctor checks
- project doctor checks
- greenfield project init
- brownfield project init with `.candidate` conflict handling
- public/private configuration separation

## Files Added Or Updated

- `docs/concepts/workplace-init.md`
- `docs/concepts/project-init.md`
- `docs/concepts/public-private-config.md`
- `docs/concepts/capability-resolution.md`
- `docs/authoring/workplace-configuration.md`
- `docs/authoring/project-initialization.md`
- `docs/validation/doctor-workplace.md`
- `docs/validation/doctor-project.md`
- `schemas/terms.schema.json`
- `schemas/*-registry.schema.json`
- `schemas/workplace-init-answers.schema.json`
- `schemas/project-init-answers.schema.json`
- `templates/workplace.yaml`
- `templates/terms.yaml`
- `templates/registries/*.yaml`
- `templates/workplace-init.answers.yaml`
- `templates/project-init.answers.yaml`
- `templates/process-forge.yaml`
- `templates/process-forge.local.yaml`
- `templates/project-*-template.md`
- `processes/workplace-initialization.yaml`
- `processes/project-initialization.yaml`
- `tools/processforge.py`
- `examples/processforge-init/**`

## Commands Implemented

```bash
python tools/processforge.py init-workplace --root <workplace-root> --dry-run
python tools/processforge.py init-workplace --root <workplace-root> --apply
python tools/processforge.py doctor-workplace --root <workplace-root>
python tools/processforge.py init-project --project-root <project-root> --workplace <workplace.yaml> --dry-run
python tools/processforge.py init-project --project-root <project-root> --workplace <workplace.yaml> --apply
python tools/processforge.py doctor-project --project-root <project-root>
```

## Behavior

- `init-workplace --dry-run` prints the planned files and writes nothing.
- `init-workplace --apply` creates `AGENTS.md`, `workplace.yaml`, `terms.yaml`, registries, `cache/`, `runtime/`, `logs/`, and an init report.
- `doctor-workplace` validates required files and warns when optional MCP providers are not configured.
- `init-project --dry-run` supports a non-existing greenfield root and prints the proposal.
- `init-project --apply` creates public and private project files, reports, review, project package draft, and `.gitignore`.
- Brownfield conflicts, including `.gitignore` conflicts, create `.candidate` files unless `--force` is used.
- `doctor-project` checks public/private separation, local config ignore policy, workplace reachability, project package draft, and init artifacts.
- `doctor-project` fails when required capabilities in the resource matching report remain unresolved, except for built-in local execution capabilities.

## Residual Risks

- YAML handling is intentionally lightweight. The tool uses PyYAML if available and a small mapping-only fallback otherwise.
- Cross-file semantic validation is still limited.
- Resource matching is heuristic and should be hardened with a formal registry parser. Built-in capabilities such as `repository.read` and `markdown.editing` are treated as resolved by the local execution context.
- Doctor checks validate MVP structure, not full process execution.

## Recommendation

Use this as the MVP init layer and harden parser/semantic checks after real project usage.
