# Resource Authoring Processes Handoff

Status: ready for verification.

## What Changed

- New workplace resource authoring processes are registered in `.pf/process-forge.yaml`.
- New CLI commands create and validate templates, knowledge packages, and platform contracts.
- `project-onboard` can select a platform contract by `project_type_hints` and include linked resources in the project snapshot.
- `release-check` blocks public script wrappers, public PowerShell references, and public Python cache directories.

## Main Verification Command

```bash
python tools/smoke_resource_authoring_processes.py
```

## Follow-Up

- Add richer template rendering tests when template application becomes part of the CLI.
- Add active tool/MCP health checks when external provider validation becomes a release target.
