# Capability Resolution

ProcessForge core is domain-neutral. It knows how to resolve capabilities, but
it does not know which user or workplace capabilities exist.

A capability is an opaque string id. Processes may require capability ids, and
specializations, tools, MCP providers, templates, platform contracts, packages,
or project overrides may provide capability ids through workspace or project
data. The resolver only computes set membership:

```text
required_capabilities
provided_capabilities
satisfied = required intersect provided
unsatisfied = required - provided
```

No user process capability is satisfied by ProcessForge core by default. PF
internal operations such as schema validation, hashing, snapshot writing, and
archive checking are runtime mechanics; they are not providers for user process
requirements.

## Data Sources

Provided capabilities can come from active data only:

- selected specialization definitions
- matched specialization `platform_bindings`
- activated tool, MCP, and template definitions
- platform contracts when explicitly selected by workspace/project data
- project overrides and task-explicit resources
- optional workplace, project, or package capability registries

If a process requires a capability that the active resource profile does not
provide, the result is `unsatisfied` and the context status is
`needs_resources`.

`doctor-project` reports missing required capabilities as registry declaration
gaps. That means no active provider declared the capability; it is not proof
that the runtime lacked actual access. Prefer registering the real provider in
the workplace. If local runtime access was independently verified and the
registry mismatch is accepted for the current delivery, record an explicit
waiver in `.pf/artifacts/capability-waivers.yaml`:

```yaml
schema_version: 1
capability_waivers:
  - capability: filesystem.read
    status: active
    reason: runtime access verified; registry provider declaration is pending
    evidence: .pf/artifacts/delivery-report.md
```

An active waiver downgrades the `doctor-project` capability gap to `WARN`; it
does not satisfy capability resolution or mutate workplace registries.

## Examples

Documentation examples use synthetic ids such as:

```text
fixture.capability.a
fixture.capability.b
example.capability.domain-specific-thing
```

Concrete software, media, legal, or other domain-shaped ids may appear only as
examples in user/workplace/package data. They are never PF core defaults.
