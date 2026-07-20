# Doctor Context

`doctor-context` validates the session bootstrap and context layer for a
project. Project context snapshot is the preferred proof point; context-index
files are compatibility artifacts under `.pf/contexts/`.

## Command

```bash
python bin/pf.py doctor-context --project-root <project-root>
```

Optional assignment freshness check:

```bash
python bin/pf.py doctor-context --project-root <project-root> --assignment <assignment-path>
```

## Checks

The command checks the context artifacts that exist for the project:

- project manifest exists under `.pf/`
- public project manifest has no local absolute paths
- project context snapshot YAML and MD exist when snapshot mode is used
- snapshot freshness is `fresh`
- context index, resolved rules, and conflict report are valid when present
- private cache/runtime path is ignored
- assignment ECP/conflict freshness is acceptable when an assignment is supplied

Capability availability and selected workplace resource health belong to
`doctor-project`.

## Expected Result

A healthy project returns PASS checks. A missing optional cache can be WARN.
Missing required sources, blocking conflicts, stale snapshot checks, or stale
assignment context checks are FAIL.
