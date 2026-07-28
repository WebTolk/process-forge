# Project Scan Boundaries

ProcessForge treats distribution, workplace, knowledge, runtime, and cache roots
as supporting resources, not normal project source.

A broad meta-project may physically contain:

```text
agents/
  processforge/
  docs/
  projects/
  snippets/
```

If `agents/` is onboarded as an `agent-workspace`, `brownfield-workspace`, or
`meta-workspace`, the project source scan excludes `processforge/`, `docs/`,
workplace registries, runtime state, and package caches by role.

Default scan policy:

```yaml
scan_policy:
  exclude_roles:
    - distribution_root
    - workplace_root
    - knowledge_root
    - runtime_root
    - package_cache
```

Knowledge roots are external resources. They may be available to context
resolution, but they are not counted as project source unless explicitly
included by a future project policy.

The ProcessForge repository itself is a project only when the project type is
explicitly `processforge-development` or `processforge-core-development`.
