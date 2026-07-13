# Instruction Conflicts

Instruction conflicts are explicit outcomes of context resolution. They should
be visible before assignment execution starts.

## Status Values

`blocked` means context compilation must stop. Examples include missing required
sources, weakening a locked hard policy, unresolved required capabilities, or
contradictory allowed and forbidden actions.

`warn` means work may continue, but the report must name the risk. Examples
include missing optional capabilities or stale cache that is not required for
execution.

`requires_approval` means the context can be compiled only when policy allows an
explicit approval. Examples include gate removal attempts or brownfield overwrite
requests.

`resolved` means the resolver found no active conflict.

## Merge Rules

Forbidden actions are unioned across sources. An allowed action cannot override a
forbidden action.

Hard policies are sticky. A lower layer can add stricter rules but cannot loosen
the hard rule.

Preferences are ordered by cascade layer. A project preference can override a
workplace preference when no locked policy is involved.

Gates are append-only unless an explicit approval path allows a change.

## Reporting

Every conflict report should include:

- global status
- blocking issues
- warnings
- approval-required issues
- resolved notes
- source fingerprints

This makes the reason for a stop or warning durable and reviewable.
