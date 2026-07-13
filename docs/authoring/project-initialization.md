# Project Initialization

Use Project Init to connect a project to ProcessForge.

## Dry Run

```bash
python tools/processforge.py init-project --project-root <project-root> --workplace <workplace.yaml> --dry-run
```

Dry run prints the planned changes and classification evidence.

## Apply

```bash
python tools/processforge.py init-project --project-root <project-root> --workplace <workplace.yaml> --apply
```

Apply writes the public and private project files. Existing brownfield files are not overwritten without `--force`.

## Review

After apply, review:

- `artifacts/project-init-proposal.md`
- `artifacts/project-classification-report.md`
- `artifacts/global-resource-matching-report.md`
- `reviews/project-init-review.md`

Observed conventions are not automatically confirmed.
