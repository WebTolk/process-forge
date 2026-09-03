# Garage Core Contract

Generated: 2026-08-24 14:45 +04

## Levels

### Level 1: Garage Essentials

Must work without daemon, Ledger session, Codex hooks, chat capture, or
Director:

- project detection;
- current snapshot read;
- process/platform/specialization summary;
- authorized knowledge/template/tool metadata;
- local search readiness;
- `pf.search`;
- `pf.resolve`;
- basic work guidance.

### Level 2: Governed Work

Adds run/task/assignment/artifact/evidence/handoff lifecycle. It must not block
Level 1 reads. If no governed work is active, Garage returns:

```yaml
work:
  governed: false
  recommendation: start_work
```

### Level 3: Forge Orchestration

Adds Runtime, Ledger, Director, leases, heartbeats, worker ownership and
session telemetry. Forge may be stricter, but must not redefine Level 1
authorization.

## Authorization

For sessionless Garage:

```text
project_root -> .pf/process-forge.yaml -> current snapshot -> allowed resource ids
```

Cross-project resource leakage is forbidden. `pf.resolve` fails closed for
resources outside the snapshot.

## Privacy

Sessionless Garage must not return private chat, other agent activity, other
project sessions, or session ownership facts.

## Preferred Path

```text
pf.context(project_root)
pf.search(project_root, query)
pf.resolve(project_root, resource_id)
pf.work.start(objective) when substantive governed work begins
```
