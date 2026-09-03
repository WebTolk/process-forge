# Project Initialization

Use Project Init to connect a project to ProcessForge.

For a non-mutating state, snapshot-health and repair-plan projection, run
`python bin/pf.py project-init-status --project-root <project-root> --json`.

The state is `complete`, `incomplete`, `repairable`, or `blocked`. It also
reports snapshot health and missing PF-owned deterministic artifacts without
exposing private filesystem paths.

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
python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic-software-project --process software-feature-development --apply
```

Apply writes the public and private project files. Existing brownfield files are not overwritten without `--force`.

Both the CLI command and the controlled MCP initialization operation use the
same Core initialization service. MCP can act only for its Ledger-bound
project and only with the JSON boolean `apply: true`.

Use `--platform <id>` and `--specialization <id>` repeatedly when those
bindings are known, and `--process <id>` for the active process. The service
persists them in the project manifest; snapshot resolution consumes that
manifest rather than MCP recomputing the bindings. A specialization is
optional when no suitable non-web specialization package is installed.

## Deterministic repair

Repair never recreates semantic/user artifacts. The current supported action
rebuilds the resolved context snapshot and then runs `doctor-project`:

```bash
python bin/pf.py project-init-repair --project-root <project-root>
python bin/pf.py project-init-repair --project-root <project-root> --apply
```

Without `--apply` the command returns a plan. The MCP counterpart is
`pf.project_initialization.repair`; omitting `apply: true` returns
`apply_required` and makes no change.

When a project has lost PF-owned deterministic files, use
`--repair-action restore_deterministic_artifacts --apply`. Existing differing
files remain `.candidate` files unless `force` is explicitly requested by the
initialization workflow; semantic/user files are not removed.

## Review

After apply, review:

- `.pf/artifacts/project-init-proposal.md`
- `.pf/artifacts/project-classification-report.md`
- `.pf/artifacts/global-resource-matching-report.md`
- `.pf/reviews/project-init-review.md`

Observed conventions are not automatically confirmed.
