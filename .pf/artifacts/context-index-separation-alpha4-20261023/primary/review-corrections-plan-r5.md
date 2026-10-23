# Accepted final review round 2 corrections

The immutable r15 candidate and review-final-r2/report.md remain CODE NO-GO.
The actual reviewer reproduced two further defects through real SQLite and Main
post-commit replay. Both corrections fit the current valid primary review-fixes
Work: local_search.py, workplace_events.py and test_review_regressions.py.

1. A previously resolved required root disappearing during collection is a
   document_scan_failed error, preserving the last database. Missing optional
   source children, deliberate containment exclusions and existing empty roots
   keep their existing meanings. Check the required root again when a source
   disappears between the initial stat and source stat.
2. Event deduplication prevents duplicate audit rows, but never substitutes for
   successful required invalidation. Replay retries the notification before
   returning an existing event. Persistent notification failure must keep the
   actual native three-event post-commit effect pending on every retry. Recovery
   delivers the notifications and completes without duplicate journal rows.

Add failing regressions first, then the bounded fixes, full candidate QA and a
fresh independent native review. No delivery, scheduler registration, backend
expansion, infrastructure operation or change to other Work scopes is authorized
by this correction plan. All earlier rejected candidates and receipts are kept.
