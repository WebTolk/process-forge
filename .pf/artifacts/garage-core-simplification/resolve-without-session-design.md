# Resolve Without Session Design

Generated: 2026-08-24 14:45 +04

## Target

`pf.resolve(project_root, resource_id)` works without Ledger session.

## Flow

1. Resolve project root and `.pf`.
2. Read current snapshot.
3. Verify the requested resource exists in snapshot-resolved resources.
4. Resolve `path_ref` through the workplace manifest into a private local root.
5. Return canonical resource metadata plus the local root only for the
   authorized resource.

## Denial

If the resource is not in the snapshot, return a closed denial:

```yaml
resource:
  id: ...
  status: denied
  reason: not_in_project_snapshot
```

Session-aware mode may add audit data, but must not change authorization.
