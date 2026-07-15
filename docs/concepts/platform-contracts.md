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
