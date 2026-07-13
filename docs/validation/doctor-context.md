# Doctor Context

`doctor-context` validates the session bootstrap and context resolution layer for
a project.

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

- `process-forge.yaml` exists
- public project manifest has no local absolute paths
- context index exists
- resolved rules exist
- conflict report exists and has no blocking status
- required source fingerprints are present
- required capabilities are resolved or treated as built in
- private cache path is ignored
- ECP is fresh for the supplied assignment when an assignment is provided
- public/private policy is not violated

## Expected Result

A healthy project returns PASS checks. A missing optional cache is a WARN. Missing
required sources, blocking conflicts, or stale ECP checks are FAIL.
