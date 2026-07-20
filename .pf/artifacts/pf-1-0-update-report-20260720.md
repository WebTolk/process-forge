# ProcessForge 1.0.0 version and update report

Date: 2026-07-20

## Scope

Raise ProcessForge to `1.0.0`, verify the repository release, inspect the update mechanism, and test updating the machine installation from the `0.1.0` line to `1.0.0`.

## Repository version

- `VERSION`: `1.0.0`
- `tools/processforge.py`: `PROCESSFORGE_VERSION = "1.0.0"`
- Spec version: `1.0`
- Schema bundle version: `1.0`
- Release archive version: `1.0.0`
- Project dogfood manifest `.pf/process-forge.yaml`: `process_forge.version: 1.0.0`, `version_constraint: "^1.0"`

## Update mechanism

ProcessForge update checks are file-first and local-distribution based.

- `self-update-check` reads `updates/processforge-update-index.yaml` from a distribution root.
- `project-upgrade-check` compares the requested/current project version with the same update index and writes `.pf/artifacts/processforge-update-assessment.md`.
- The current implementation reports whether an update exists, the latest version, migration requirement, guide path, and affected project files.
- The current implementation does not download or self-replace the distribution automatically. Installing the new distribution is an external controlled replacement of the distribution directory.

## Update index

The stable channel now resolves:

- current version tested: `0.1.0`
- latest version: `1.0.0`
- migration required: `False`
- migration guide: `updates/migrations/1.0.0-stable-release.md`

## Machine installation test

Machine installation path: `D:\.agents\process-forge`

Previous installed copy was backed up to:

- `D:\.agents\process-forge.backup-20260720-105640`

The validated `dist/processforge-v1.0.0.zip` archive was extracted into `D:\.agents\process-forge`.

Installed version after replacement:

```text
ProcessForge 1.0.0
Spec: 1.0
Schema bundle: 1.0
```

The external workplace registry at `D:\.agents\pf-workplace\registries\distributions.yaml` was updated to record the installed distribution as `1.0.0`.

## Verification

Repository checks:

- `python bin\pf.py version` -> `ProcessForge 1.0.0`
- `python tools\validate-process-forge-schemas.py --root .` -> pass
- `python tools\validate-public-cleanliness.py --root .` -> pass
- `python tools\validate-process-forge-checksums.py --root . --write` -> pass
- `python bin\pf.py release-test --root .` -> pass
- `python bin\pf.py release-pack --root . --output dist\processforge-v1.0.0.zip` -> wrote archive and manifest with 369 files
- `python bin\pf.py release-archive-test --archive dist\processforge-v1.0.0.zip` -> pass

Installed distribution checks:

- `python D:\.agents\process-forge\bin\pf.py version` -> `ProcessForge 1.0.0`
- `python D:\.agents\process-forge\bin\pf.py self-update-check --distribution-root D:\.agents\process-forge --current-version 0.1.0` -> update available to `1.0.0`
- `python D:\.agents\process-forge\bin\pf.py self-update-check --distribution-root D:\.agents\process-forge` -> no update for `1.0.0`
- `python D:\.agents\process-forge\bin\pf.py doctor-workplace --root D:\.agents\pf-workplace` -> pass

Project upgrade check:

- `python D:\.agents\process-forge\bin\pf.py project-upgrade-check --project-root . --current-version 0.1.0` wrote `.pf/artifacts/processforge-update-assessment.md`
- The assessment reports status `requires_approval`, available version `1.0.0`, migration required `False`, and the `1.0.0` migration guide.

## Result

ProcessForge repository and the machine installation are on `1.0.0`. The update path from `0.1.0` to `1.0.0` is visible through the update index and was tested against the installed distribution. The release archive is validated as an installable artifact.
