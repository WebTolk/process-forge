# Example Child Platform Inheritance

Create or import `docs.example-parent` and `docs.example-child` before creating
the child platform. The child platform resolves as
`platform.example-parent -> platform.example-child`.

```yaml
id: platform.example-child
title: "Example Child Platform"
type: platform_contract
version: "1.0.0"

extends:
  - id: platform.example-parent
    required: true

requires:
  platforms:
    - id: platform.example-parent
      required: true
  knowledge_packages:
    - docs.example-child

includes:
  knowledge_packages:
    - id: docs.example-child
      required: true
      load_policy: on_demand
```

`project-onboard --type example-child-project` records `platform_stack` as
`platform.example-parent`, then `platform.example-child`. The resulting
`knowledge_stack` includes inherited parent packages plus the child package.
