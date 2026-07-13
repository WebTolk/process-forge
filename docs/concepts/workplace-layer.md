# Workplace Layer

The workplace layer describes what is available on the current machine or execution host.

It answers:

```text
What capabilities, paths, tools, caches, and policies are available here?
```

It does not describe project-specific rules.

## Workplace Manifest

A workplace manifest should include:

- workplace id and name
- type and operating system
- root paths
- available platform packages
- available knowledge package roots
- available tools
- available MCP servers
- cache paths
- runner capabilities
- local policies
- locked policies
- fallback tools

## Boundary

Workplace rules describe local availability. Organization or company rules should be represented as knowledge packages, not as workplace state.
