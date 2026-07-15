# Handoff: codex -> maintainer

Objective:
Implement ProcessForge Resource Management MVP from `processforge_resource_management_mvp_master_prompt.md`.

Current status:
Implemented and smoke-tested locally. Final checksum and full validation should be treated as the current proof point after this handoff is refreshed.

Input artifacts:
- `задания/processforge_resource_management_mvp_master_prompt.md`
- `.pf/AGENTS.md`
- `.pf/process-forge.yaml`

Files changed:
- `tools/processforge.py`
- `tools/smoke_resource_management.py`
- `schemas/*resource*.schema.json`, `schemas/tool-definition.schema.json`, `schemas/mcp-definition.schema.json`
- `processes/*resource*.yaml`, `processes/*register.yaml`, `processes/*install.yaml`
- `templates/*resource*.yaml`, `templates/*definition.yaml`
- `docs/concepts/resource-management.md` and related concept/authoring docs
- `.pf/contexts/project-context.snapshot.*`

Files not to touch:
- `.pf/runtime/` outputs are private runtime state and should not be committed unless policy changes.

Known issues:
- Tool/MCP healthchecks are declarative only.
- Documentation import does not download content.
- Resource URL availability is not probed by doctor.

Required checks:
- `python -m py_compile tools/processforge.py tools/smoke_resource_management.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/validate-process-forge-checksums.py --root . --check`
- `python tools/processforge.py events-validate --project-root .`
- `python tools/processforge.py doctor-project --project-root .`
- `python tools/smoke_resource_management.py`

Next recommended action:
Review the MVP command UX after first real workplace resource addition and decide whether registry healthcheck execution belongs in a future runner.
