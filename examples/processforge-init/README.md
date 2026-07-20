# ProcessForge Init Examples

These examples show the expected inputs for workplace and project initialization.

## Workplace

Use the workplace answers template:

```bash
python bin/pf.py workplace-init --workplace <workplace-root> --dry-run
```

## Greenfield Project

```bash
python bin/pf.py project-onboard --project-root <empty-project-root> --workplace <workplace-root> --type generic-software-project --dry-run
```

## Brownfield Project

```bash
python bin/pf.py project-onboard --project-root <existing-project-root> --workplace <workplace-root> --type generic-software-project --dry-run
```

Dry run does not write files. Apply mode writes files and protects existing brownfield files by creating `.candidate` files unless `--force` is used.
