# Capability Resolution

ProcessForge processes should ask for capabilities, not concrete tools.

## Capability

A capability names what must be possible:

```text
repository.read
repository.symbol_analysis
php.static_analysis
official_documentation
browser.automation
media.generate
```

## Provider

A provider is a configured tool or MCP server that can satisfy a capability.

Examples:

- a static analyzer executable
- a documentation lookup MCP server
- a browser automation MCP server
- a package builder

## Resolution Order

1. Project-local provider.
2. Workplace provider.
3. Optional fallback provider.
4. Missing capability report.

Required missing capabilities block doctor checks. Optional missing capabilities produce warnings.

## Public Boundary

Public manifests record capability ids and selected package ids. Private local config records concrete paths and local preferences.
