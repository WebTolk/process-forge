# WTAICC Future Compatibility

ProcessForge keeps events and hooks compatible with future WTAICC without
implementing WTAICC in the MVP.

Processes declare emitted events. Project `.pf/hooks.yaml` routes matching
events to outbox targets by default. Network webhook sending is disabled unless
a future transport explicitly enables it.

The default WTAICC-compatible hook is:

```yaml
event_types:
  - "*"
target:
  type: outbox
```

Chat export remains opt-in. Chat events support actors such as operator,
orchestrator, agent, subagent, system, and tool.

Future WTAICC can read update metadata, notify projects, schedule migration
tasks, and track which projects use which ProcessForge version.
