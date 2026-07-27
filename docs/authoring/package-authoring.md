# Package Authoring

A knowledge package is a versioned bundle of rules, references, resources,
templates, procedures, quality rubrics, and capability requirements.

Use packages for organization, direction, specialization, platform, toolchain,
project, process, task, or agent-profile knowledge.

## Schema-Required Fields

`schemas/package-manifest.schema.json` currently requires:

- `schema_version`
- `id`
- `name`
- `version`
- `kind`
- `scope`

## Optional Or Recommended Fields

These fields are supported by the schema and local tooling, but they are not
schema-required for every package:

- `package_root`
- `description`
- `dependencies`
- `rules`
- `templates`
- `resources`
- `tools`
- `mcp_servers`
- `validation`

Resource entries inside `resources` have their own required fields:
`id`, `kind`, `title`, and `load_policy`.

## Update Sites

Packages that should receive updates can declare `update_sites` with
`manifest_url`, `changelog_url`, trust policy, and operator notification policy.
See `docs/authoring/update-sites-for-packages.md` for the unified package
contract and tool-specific policy rules.
