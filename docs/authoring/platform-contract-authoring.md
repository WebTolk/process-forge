# Platform Contract Authoring

Platform contracts compose required and recommended capabilities, packages, tools, MCP, and templates.

ProcessForge core is domain-agnostic. It does not know about specific
implementation, documentation, content, operations, or business domains.
Platform behavior comes from manifests and policy data.

Use platform contracts for domain or application stacks, not for base language
or web-technology knowledge. Base technologies should be authored as knowledge
packages and capabilities first, then included from the domain platform that
needs them.

Do not create platform contracts for base technology knowledge. Create
knowledge packages and capabilities first, then include them from the platform
contract that needs them.

Create and validate a contract through the Python launcher:

```bash
python bin/pf.py platform-create --workplace ./workplace --id platform.example-app --title "Example Application Platform" --project-type example-app --apply
python bin/pf.py platform-contract-doctor --workplace ./workplace --platform platform.example-app
```

Use `requires` for items that make the platform unsafe or incomplete when missing. Doctor checks should fail when required contracts or required resources are absent.

Use `includes` for recommended knowledge, templates, tools, and MCP providers. Missing recommended entries should warn.

Keep required and recommended lists separate so snapshots can render them clearly and doctor output can map missing entries to FAIL or WARN.

`project_type_hints` connects the contract to `project-onboard`. When a project is onboarded with a matching type, the project context snapshot records the platform and linked resources by id.

Create or register dependencies before creating the platform contract: knowledge packages, reusable templates, tools, MCP servers, processes, coding standards, and capabilities.

Use `extends` for inheritance and `requires.platforms` for dependency checks.
Joomla -> JoomShopping is only an example; any parent/child stack can be
declared the same way by manifest.

Run `platform-contract-doctor` after authoring. It resolves the parent-first platform stack, checks missing parents and circular inheritance, checks inherited required resources, and writes a resolved stack snapshot.
