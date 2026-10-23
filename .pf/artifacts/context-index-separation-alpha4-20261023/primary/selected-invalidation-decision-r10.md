# Make a clean successful batch usable without full reindexing

Supersedes only the blanket no-acknowledgement rule of batch-design-r7. Unknown,
unselected, old failed/interrupted or concurrently changed work still cannot be
acknowledged by a selected pass. A completed batch whose pending notifications
are ALL explicitly bound to its successful qualified IDs can acknowledge them.

The existing opaque invalidation token remains authoritative for cheap readers.
The canonical owner additionally publishes one small uniquely named durable
notification before that token, binding its identity to qualified resource IDs
or marking it unknown. Only native knowledge-add-batch audit events with known
package/resource identity use a qualified notification; other routes remain
unknown and require full maintenance. Concurrent writers publish independent
notifications. No shared read/modify/write set, scheduling or source scan.

Under the same canonical writer lock, capture pending notifications, current token
and prior maintenance state. A resources pass may acknowledge only a complete
known selection with no previous failure, and no new token during execution.
Full maintenance can acknowledge all captured notifications. Retire only those
exact captured private notification files while durable state is still running,
then persist terminal receipt with their IDs. Failure/interruption preserves a
blocking running/failed state; new notifications are never removed by age or scope.

After selected document replacement, the existing SQLite backend may publish a
new catalogue metadata state without opening unselected documents, only if every
live enabled resource has matching stored identity/fingerprint/policy/root/version
and no extra orphan row remains. Use stored document fingerprints for generation
and preserve the prior last_full_reconciliation. A required generic invalidation
or failed state still blocks public observation even if physical metadata matches.
Missing or changed unselected metadata keeps the catalogue stale. Full verified
manual/future scheduled maintenance remains separate; workplace_reconciled=false.

No new storage backend, general DAL, log-coupled state machine, Runtime operation
or public query/access change. Existing primary review-fix Core scope owns these
sequential changes. Native batch output remains immutable; new actual CLI proof
must demonstrate fresh known coverage after successful partial indexing and a
later explicit full pass updating an intentionally unselected changed document.
Add mixed/unknown/raced notification, interruption/publication and metadata-drift
tests; repeat full QA and obtain independent native CODE GO before delivery.
