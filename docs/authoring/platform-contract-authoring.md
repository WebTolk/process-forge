# Platform Contract Authoring

Platform contracts compose required and recommended capabilities, packages, tools, MCP, and templates.

Use `requires` for items that make the platform unsafe or incomplete when missing. Doctor checks should fail when required contracts or required resources are absent.

Use `includes` for recommended knowledge, templates, tools, and MCP providers. Missing recommended entries should warn.

Keep required and recommended lists separate so snapshots can render them clearly and doctor output can map missing entries to FAIL or WARN.
