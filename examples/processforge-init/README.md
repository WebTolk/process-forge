# ProcessForge Init Examples

These examples show the expected inputs for workplace and project initialization.

## Workplace

Use the workplace answers template:

```bash
python tools/processforge.py init-workplace --root <workplace-root> --answers templates/workplace-init.answers.yaml --dry-run
```

## Greenfield Project

```bash
python tools/processforge.py init-project --project-root <empty-project-root> --workplace <workplace.yaml> --answers examples/processforge-init/greenfield/project-init.answers.yaml --dry-run
```

## Brownfield Project

```bash
python tools/processforge.py init-project --project-root <existing-project-root> --workplace <workplace.yaml> --answers examples/processforge-init/brownfield/project-init.answers.yaml --dry-run
```

Dry run does not write files. Apply mode writes files and protects existing brownfield files by creating `.candidate` files unless `--force` is used.
