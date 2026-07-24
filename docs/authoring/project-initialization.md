# Project Initialization

Use Project Init to connect a project to ProcessForge.

## Dry Run

For dry-run, `<project-root>` must already exist because the command inspects the
target directory before writing. Apply mode can create a missing greenfield
project root.

```bash
python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic-software-project --dry-run
```

Dry run prints the planned changes and classification evidence.

## Apply

```bash
python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic-software-project --apply
```

Apply writes the public and private project files. Existing brownfield files are not overwritten without `--force`.

## Review

After apply, review:

- `.pf/artifacts/project-init-proposal.md`
- `.pf/artifacts/project-classification-report.md`
- `.pf/artifacts/global-resource-matching-report.md`
- `.pf/reviews/project-init-review.md`

Observed conventions are not automatically confirmed.
