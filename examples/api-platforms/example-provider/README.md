# Example Provider API Platform

API packages use provider-specific ids. Do not create one generic `docs.api`
package for all providers.

```text
package id:   docs.api.example-provider
platform id:  platform.api-example-provider
registry id:  api-example-provider
```

```yaml
id: platform.api-example-provider
title: "Example Provider API Platform"
type: platform_contract
version: "1.0.0"

requires:
  knowledge_packages:
    - docs.api.example-provider

includes:
  tools: []
  mcp: []
```

Private API exports, downloaded specs, and local examples should be referenced
through workplace roots, not embedded as private absolute paths in public
package or index YAML.
