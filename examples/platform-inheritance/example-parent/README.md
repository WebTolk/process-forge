# Example Parent Platform Inheritance

Create or import `docs.example-parent` before creating
`platform.example-parent`.

```yaml
id: platform.example-parent
title: "Example Parent Platform"
type: platform_contract
version: "1.0.0"

project_type_hints:
  - example-parent-project

requires:
  capabilities:
    - filesystem.read
    - filesystem.write
  knowledge_packages:
    - docs.example-parent

includes:
  knowledge_packages:
    - id: docs.example-parent
      required: true
      load_policy: on_demand
```

The parent platform owns shared context and common knowledge resources. Child
platforms inherit those records through `extends`.
