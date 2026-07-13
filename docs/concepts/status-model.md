# Status Model

Statuses are machine-readable ids.

## Artifact Statuses

- `missing`: required artifact does not exist yet.
- `draft`: artifact exists and is still being worked on.
- `ready_for_review`: artifact is ready for review.
- `approved`: artifact passed review and is protected.
- `rejected`: artifact failed review and needs changes.
- `stale`: artifact was invalidated by changed context.
- `superseded`: artifact was replaced by a newer artifact.
- `archived`: artifact is retained for history only.

## Review Results

- `pass`
- `pass_with_conditions`
- `warn`
- `fail`
- `skipped`

## Upgrade Assessment Results

- `safe`
- `requires_approval`
- `requires_migration`
- `blocked`
