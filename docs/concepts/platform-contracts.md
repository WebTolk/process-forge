# Platform Contracts

A platform contract is a composition package, not only a label.

It can include:

- platform knowledge packages
- required capabilities
- language and toolchain packages
- official documentation references
- source code references
- snippets and examples
- templates
- tools
- MCP providers
- local test environment notes

Project initialization can select a platform contract from explicit operator
input, `project_type_hints`, or generic detection rules declared by platform
manifests. ProcessForge core does not know about specific implementation,
documentation, content, operations, or business domains. Platforms are
data-driven contracts loaded from manifests.

## Capability, Knowledge Package, Platform

- A capability says what the agent or process may need to do.
- A knowledge package says where the agent should read rules, documentation,
  examples, and standards.
- A platform contract composes an application or domain stack over packages,
  templates, tools, MCP providers, capabilities, and processes.

Base languages and web technologies belong to capabilities and knowledge
packages. They are not platform contracts. A project platform may include that
knowledge directly or inherit it from a parent platform.

Resource authoring uses `platform-create` to write contracts under the workplace
platform contract root. `project_type_hints` is the bridge to `project-onboard`:
matching hints add the platform to the project snapshot together with linked
knowledge packages and templates.

Missing required platform capabilities block strict automation. Missing
optional capabilities produce warnings.
# Resource Management Contract Use

Platform contracts may reference knowledge packages, knowledge resources, tools, MCP providers, and templates through separate required and recommended groups.

- `requires` means missing entries are blocking and doctor checks should FAIL.
- `includes` means missing entries are advisory and doctor checks should WARN.

Contracts are composition packages. They do not copy heavy resources into projects; snapshots include selected resource index records with `load_policy`.

Use `extends` for inheritance and `requires.platforms` for dependency checks:

```yaml
extends:
  - id: platform.example-parent
    version: "^1.0"
    required: true

requires:
  platforms:
    - id: platform.example-parent
      version: "^1.0"
      required: true
```

Parent platforms resolve first. Their resources merge before the child platform is applied. `project-onboard` records the deterministic `platform_stack` and inherited knowledge packages.

Do not start by creating a platform contract if its required packages, templates, tools, MCP servers, processes, coding standards, or capabilities do not exist yet. Create or register dependencies first.

Example only: a documentation page may describe a real stack such as
Joomla -> JoomShopping, where the child platform inherits the parent context.
That kind of product-specific stack belongs in workplace data or docs/examples,
not in ProcessForge core code paths.
## Platform Versus Specialization

Platform contracts describe where the work happens. They do not encode roles.
Use a specialization for role or work-mode selection, and use
`platform_bindings` inside that specialization to choose platform-specific
knowledge, tools, MCP providers, and templates.
