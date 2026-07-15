# Assignment: ProcessForge Session Bootstrap Implementation

## Status

active

## Objective

Implement the file-only ProcessForge session bootstrap and context resolution MVP.

## Scope

- session start request model
- session bootstrap protocol
- context index model
- resolved rules model
- instruction conflict policy
- context cache model
- context capsule model
- CLI commands for session and context operations
- validation, review, and implementation reports

## Allowed Files

- `docs/concepts/**`
- `docs/validation/**`
- `schemas/**`
- `templates/**`
- `processes/**`
- `tools/**`
- `artifacts/**`
- `reviews/**`
- `logs/**`
- `README.md`
- `process-forge.yaml`
- `.gitignore`

## Required Checks

- `python tools/validate-process-forge-schemas.py`
- `python tools/validate-public-cleanliness.py`
- `python tools/validate-process-forge-checksums.py`
- `python tools/processforge.py --help`
- `python tools/processforge.py context-resolve --project-root .`
- `python tools/processforge.py doctor-context --project-root .`

## Notes

Keep the implementation file-only. Do not add backend, database, web UI, or mandatory runner dependencies.
