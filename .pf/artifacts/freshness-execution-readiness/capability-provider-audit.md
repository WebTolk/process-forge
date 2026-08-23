# Capability Provider Audit

Дата: 2026-08-23

## Checked Model

Capability requirements and providers stay separate:

- platform contracts may require capabilities;
- specializations may select resources and provide profile capabilities;
- project/workplace registries declare actual tool/MCP providers;
- process/stage requirements describe work obligations;
- snapshot records the resolved state.

## Result

No Joomla-specific provider was added.

No artificial `filesystem.read/write` provider was registered to make tests
green. Missing capabilities are reported as:

```yaml
execution_readiness:
  status: blocked
  missing_capabilities:
    - capability: filesystem.read
      required_by: project.required_capabilities
      availability: missing
    - capability: filesystem.write
      required_by: project.required_capabilities
      availability: missing
```

## Provider Semantics

Expected provider scope is explicit:

- project or workplace tool/MCP registry for project required capabilities;
- specialization resource profile, active process pack, or workplace registry
  for execution-route capabilities.

Platform requirements are not treated as providers.
