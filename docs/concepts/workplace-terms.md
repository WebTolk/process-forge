# Workplace Terms

`terms.yaml` maps human phrases to ProcessForge registries and resource scopes.

The registry supports aliases such as:

- `local knowledge base`
- `local knowledge`
- `knowledge folders`
- `documentation roots`
- `project knowledge base`
- `platform knowledge`
- `global templates`
- `project templates`
- `global tools`
- `MCP`

Terms can include `resolves_to` metadata so agents can map a user phrase to a
registry, resource type, or project path before loading files.

The global agent section should stay short and point agents to the workplace
manifest, terms registry, and project `.pf/AGENTS.md`.
