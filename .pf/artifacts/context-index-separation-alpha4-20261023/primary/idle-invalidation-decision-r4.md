# Idle invalidation compatibility and exact scope boundary

PF refused a proposed one-file operational-smoke scope with work_scope_conflict.
No conflicting Work was canceled/reused and that smoke file remains unchanged.
The rejected proposed adaptation is retained in native-smoke-handoff-r3.md; it is
not the final implementation decision. The existing valid correction scope owns
the Core files required for the following compatible implementation.

The notification first publishes the required opaque atomic token. It then tries
the same canonical OS writer lock exactly once, without waiting. If acquired,
the backend's existing mark_dirty operation retains the released idle SQLite
status/reason/counters. Only explicit workplace scope marks all cached scopes;
project snapshots keep their prior scoped behavior. The SQLite busy timeout for
this metadata update is zero. If either lock/SQLite update is refused, the token
remains authoritative and pending, so no notification is lost or success state
silently overwrites it. This optional metadata projection performs no source scan,
index build, enqueue, background work or waiting for an active writer.

Main and resource events call the common component. Low-level backend operations
remain available for the existing engine/adapter contract and tests; they are not
independent application entrypoints with PF authorization or state guarantees.
The original r1 dirty probe must use the corrected actual Main/event entrypoint
when checking the application invariant. Actual event-path regression tests prove
both lossless notification during collection/terminal publication and absence of
SQLite writes while a canonical writer holds its lock.

Pending invalidation also no longer blocks explicit repair of a derived schema
mismatch/missing schema: the known invalid-schema dirty failure is left to the
immediately following maintenance/rebuild operation. Other backend errors still
fail and preserve the pending notification. A real schema-mismatch regression
failed before this correction and passed after it. Required token/state/report
publication errors are never treated as optional.
