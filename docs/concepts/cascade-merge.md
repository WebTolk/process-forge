# Cascade Merge

ProcessForge builds an execution context by merging sources from least specific to most specific.

Markdown instruction files such as `AGENTS.md` are not machine parameter
sources. If a station or global profile needs to contribute machine-readable
parameters, it must expose a structured YAML or JSON source explicitly. In the
default local/workplace mode, parameter value resolution starts at `workplace`.

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
- Lists without item ids are replaced by the more specific list.
- `null` deletes a map value from a more general layer.
- Locked policies cannot be overridden without explicit permission.
- Blocking conflicts stop execution context assembly.
- The final context records every source and package/template version.
- Task-level overrides must be explicit and logged.

## Parameters

`parameters` is a neutral tree. ProcessForge does not attach domain meaning to
keys such as `test_stands`, `brand_channels`, `tax_profiles`, or
`render_presets`; it only merges objects by the cascade rules and records
provenance.

Parameter values may be declared by structured workplace, specialization,
platform, project, process, stage, task, or agent-profile sources when those
sources are active. Organization and direction layers are optional and can be
added later without changing the merge rules.

Inline local credentials are ordinary parameter values for the resolver.
Portable/public exports should prefer `auth_ref` or `secret_ref` and sanitize
inline secrets according to export policy.

The current file-first sources are:

- workplace manifest `parameters`
- workplace `registries/parameters.yaml`
- active platform contract `parameters`
- active specialization `parameters`
- project manifest `parameters`
- project local overrides `overrides.parameters`
- project `.pf/parameters.yaml`
- project `.pf/parameters.local.yaml`
- process definition, stage, and assignment `parameters` when active

Example:

```yaml
# <workplace-root>/registries/parameters.yaml
schema_version: 1
kind: processforge.parameters
scope: workplace
parameters:
  test_stands:
    - id: local-joomla
      url: http://joomla.local/administrator/
      user: codex
      auth_ref: local.joomla.admin
```

```yaml
# <project-root>/.pf/process-forge.local.yaml
overrides:
  parameters:
    test_stands:
      - id: local-joomla
        user: project-user
        auth_ref: project.local.joomla.admin
```

The resulting `resolved_parameters.test_stands` keeps one `local-joomla` item
and merges the project auth reference into the workplace object by `id`. A more
specific list item can set `_delete: true` or `__delete__: true` to remove an
inherited item.

## Conflict Classes

- `informational`: record only.
- `warning`: continue with review note.
- `blocking`: stop context assembly until resolved.
