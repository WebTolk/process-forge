# Cascade Merge

ProcessForge builds an execution context by merging sources from least specific to most specific.

## Order

```text
core defaults
< workplace
< organization
< direction
< specialization
< platform
< toolchain
< project
< process
< stage
< task
< agent profile
```

## Rules

- Packages are loaded by dependency graph before specificity.
- Scalar values are replaced by more specific values.
- Maps merge recursively.
- Lists merge by `id` when list items have ids.
- Locked policies cannot be overridden without explicit permission.
- Blocking conflicts stop execution context assembly.
- The final context records every source and package/template version.
- Task-level overrides must be explicit and logged.

## Conflict Classes

- `informational`: record only.
- `warning`: continue with review note.
- `blocking`: stop context assembly until resolved.
