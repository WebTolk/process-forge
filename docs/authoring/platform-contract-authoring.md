# Platform Contract Authoring

Platform contracts compose required and recommended capabilities, packages, tools, MCP, and templates.

Create and validate a contract through the Python launcher:

```bash
python bin/pf.py platform-create --workplace ./workplace --id platform.joomla --title "Joomla Platform" --project-type joomla-component --apply
python bin/pf.py platform-contract-doctor --workplace ./workplace --platform platform.joomla
```

Use `requires` for items that make the platform unsafe or incomplete when missing. Doctor checks should fail when required contracts or required resources are absent.

Use `includes` for recommended knowledge, templates, tools, and MCP providers. Missing recommended entries should warn.

Keep required and recommended lists separate so snapshots can render them clearly and doctor output can map missing entries to FAIL or WARN.

`project_type_hints` connects the contract to `project-onboard`. When a project is onboarded with a matching type, the project context snapshot records the platform and linked resources by id.
