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

Project initialization can select a platform contract from detected project
markers or operator answers. For example, a Joomla component hint selects
`platform.joomla` when the workplace registry provides it.

Missing required platform capabilities block strict automation. Missing
optional capabilities produce warnings.
# Resource Management Contract Use

Platform contracts may reference knowledge packages, knowledge resources, tools, MCP providers, and templates through separate required and recommended groups.

- `requires` means missing entries are blocking and doctor checks should FAIL.
- `includes` means missing entries are advisory and doctor checks should WARN.

Contracts are composition packages. They do not copy heavy resources into projects; snapshots include selected resource index records with `load_policy`.
