# Work Capsule isolation design

Status: ready_for_review

## Reused boundary

The existing assignment capsule is the Work Capsule; no parallel context entity will be introduced.

## Creation sequence

```text
project manifest authorization
  -> normalize allowed/default process selection
  -> resolve one selected process definition
  -> resolve active specializations and resources for that selection
  -> pin Run + Assignment + immutable capsule
```

## Capsule contents

The effective capsule must contain only:

- snapshot identity/checksum;
- one active process descriptor and fingerprint;
- current stage and obligations;
- active specialization ids;
- selected resource identities;
- effective resource profile, scope, outputs, actions and gates.

It must not copy definitions or requirements from other allowed processes or specializations. The project snapshot may still contain the authorization catalog.

## Read behaviour

`pf.context` before start exposes a compact allowed-process catalog. `pf.work.state` after start exposes one active process, its stage, gates, artifacts and active specializations. The resolution/search implementation remains snapshot-authorized; process-specific resource narrowing is applied only where it is a safe filter on that existing set.

## Compatibility

Older runs without the new fields continue to use their pinned definition or legacy singular process path. New fields are additive in schemas.
