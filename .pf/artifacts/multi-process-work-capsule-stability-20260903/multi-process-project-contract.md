# Multi-process project contract

Status: ready_for_review

## Terms and invariant

- **Allowed processes** are the project authorization set.
- **Default process** is used only when selection is unambiguous.
- **Active process** is exactly one process pinned to one Work.
- **Allowed specializations** are project authorization; **active specializations** are the pinned set for a Work.
- The snapshot is the authorization universe. The Work capsule is its effective, narrow execution context.

Invariant: multiple processes may be allowed, but one Work never activates more than one process or a union of their definitions.

## Manifest compatibility

Legacy input remains valid:

```yaml
process: software-feature-development
```

It normalizes to default `software-feature-development` and an allowed set containing only that id. New input is additive:

```yaml
processes:
  default: software-feature-development
  allowed:
    - architecture-analysis
    - software-feature-development
    - testing
```

`processes` remains distinct from the existing catalog entry list. The normalizer accepts the existing list form and the new selection object, rejects malformed/duplicate ids, and never authorizes an undeclared catalog definition.

## Selection result

`pf.work.start(objective, process_id?)` has these deterministic outcomes:

1. An explicit allowed id selects that process.
2. An explicit unknown catalog id returns `process_not_found`.
3. An explicit catalog id outside the allowed set returns `process_not_allowed`.
4. One allowed process selects it.
5. With multiple allowed processes, a default selects only when it is declared as the sole safe default; otherwise return `process_choice_required`.

Choice candidates expose only `id`, `title`, `purpose`, `expected_result`, and optional recommended specializations. They never include stages, gates, prompts, artifacts, or full definitions.

## Pinning

At creation, Run, Assignment, and capsule retain `snapshot_id`, the selected `process_id`, process version/fingerprint, active specialization ids, and selected resource identities. Subsequent changes to allowed processes, specializations, or the manifest do not change that Work.

## Continuation

The completed result may advertise `next.available_processes` and a `next.recommended_process` only when a route makes it unambiguous. It may contain advisory `session_continuity` (`preserve`, `fresh`, or `auto`). Garage does not create, close, restart, or require a Codex session.
