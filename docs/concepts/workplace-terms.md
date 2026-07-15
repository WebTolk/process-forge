# Workplace Terms

`terms.yaml` maps human phrases to ProcessForge registries and resource scopes.

The registry supports Russian aliases such as:

- `локальная база знаний`
- `локальные знания`
- `папки со знаниями`
- `проектная база знаний`
- `платформенные знания Joomla`
- `глобальные шаблоны`
- `проектные шаблоны`
- `глобальные инструменты`
- `MCP`

Terms can include `resolves_to` metadata so agents can map a user phrase to a
registry, resource type, or project path before loading files.

The global agent section should stay short and point agents to the workplace
manifest, terms registry, and project `.pf/AGENTS.md`.
