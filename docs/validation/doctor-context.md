# Doctor Context

`doctor-context` validates the session bootstrap and context layer for a
project. Project context snapshot is the preferred proof point; legacy
context-index files remain supported.

## Command

```bash
python tools/processforge.py doctor-context --project-root <project-root>
```

Optional assignment freshness check:

```bash
python tools/processforge.py doctor-context --project-root <project-root> --assignment <assignment-path>
```

## Checks

The command verifies:

- project manifest exists under `.pf/` or legacy root layout
- public project manifest has no local absolute paths
- project context snapshot YAML and MD exist when snapshot mode is used
- snapshot freshness is `fresh`
- required capabilities are available
- legacy context index, resolved rules, and conflict report are valid when present
- private cache/runtime path is ignored
- ECP is fresh for the supplied assignment when an assignment is provided
- public/private policy is not violated

## Expected Result

A healthy project returns PASS checks. A missing optional cache is a WARN.
Missing required sources, blocking conflicts, or stale snapshot/ECP checks are
FAIL.
