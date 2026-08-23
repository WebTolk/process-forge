# Context Freshness

Project context freshness answers whether the current snapshot still represents
the project flow inputs.

The status is one of:

- `fresh`: the current snapshot still matches its declared requirements and resolved resources
- `fresh_with_updates`: pinned multi-version resources still exist, but newer compatible versions are available
- `stale`: rolling/current resources changed, a source fingerprint changed, or an update marked the snapshot stale
- `broken`: a required source or pinned resource instance is missing

Freshness does not answer whether the active agent can perform every current
process action. That is reported separately as execution readiness. A missing
execution capability, for example `filesystem.write`, can make
`execution_readiness.status` equal `blocked` while the context and resources
remain `fresh`.

The check output includes separate readiness projections:

```yaml
readiness:
  context:
    status: fresh
  resources:
    status: fresh
  execution:
    status: blocked
    missing_capabilities:
      - capability: filesystem.write
        required_by: project.required_capabilities
```

The check output also includes the policy action:

```text
STATUS: fresh | fresh_with_updates | stale | broken
POLICY_ACTION: continue | notify | ask_operator | notify_director | block
```

`generated_at` alone is not part of source freshness. Regenerating a snapshot
without source changes must not make the previous snapshot stale by itself.
Missing execution capabilities also do not make resolved resources stale.

Use:

```bash
python bin/pf.py project-context-check --project-root <project-root> --session-start --json
```

Refresh with:

```bash
python bin/pf.py project-context-refresh --project-root <project-root>
```
