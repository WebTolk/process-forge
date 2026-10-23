# Alpha4: governed corrections after independent CODE NO-GO

The completed independent native review r1 reproduced four real defects in the
unchanged r4 candidate. Its report and probes remain immutable. Preserve that
entire candidate at its existing path; build a separate corrected candidate.
No product source writer ran during the review. All four findings are accepted.

1. Fail closed on real fulltext file reads/stat failures and directory traversal
   errors. Preserve previous committed rows, report portable error codes, keep
   durable failure/incompleteness, and prove explicit recovery with real SQLite.
   Intentional exclusions/metadata-only policies and containment remain unchanged.
2. Capture durable maintenance identity and invalidation identity around the whole
   project read, including authorized coverage and SQL results. Discard a raced
   result without retry/wait/build and return a bounded unavailable/stale payload.
3. Route both Main and workplace resource events through the common maintenance
   owner for invalidation. Publish an atomic opaque invalidation token independently
   of the long writer lock; hash its bytes rather than trusting persisted fields.
   The writer captures that identity before collection and acknowledges only that
   identity. A notification during collection survives terminal publication. When
   pending invalidation is serviced, the backend's existing mark_dirty is invoked
   under the canonical writer lock before its explicit operation. Extend the real
   narrow backend port only by that consumed method. A project pass cannot clear
   a workplace-wide invalidation or preceding incomplete global pass.
4. Project readiness exposes only authorized resource/document counts, including
   zero authorization. Physical workplace availability remains separate. Keep
   query-time authorization, metadata-only policy, payload/error/page contracts.

Primary Main composition remains under the existing aggregate Work. Transfer the
completed primary readonly and integration-QA reservations to one governed review
fix successor, preserving their canceled handoff histories and all prior receipts.
Its disjoint scope also includes workplace_events and new behavioral regression
tests. Native contributor scopes stay unchanged. No infrastructure, scheduling
loop, new database backend, general DAL, live indexing or paused OOP work is added.

Add real-file failure/recovery, directory scan refusal, actual interleaved durable
publication failure, dirty notification during document capture and project count
isolation regressions. Repeat affected/full pytest and registered scoped quality
checks on a separate frozen candidate; obtain a fresh independent native review.
Commit/push/publication remain gated on CODE GO and complete release qualification.
