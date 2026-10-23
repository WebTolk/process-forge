# Independent review of r20 release correction

Same single logical reviewer, fresh bounded Work after complete implementation/QA.
Verify all 45 source-candidate-r20.json hashes before/after; candidate-r20 is the
only target. Read source-delta-r20.diff: exactly seven files differ from pushed
23ae1661. The 38 unchanged prior-owned files retain r16 proof. Read prior r16
review-final-r3/report.md, review-input-r5/Python/OOP/provenance and decisions.

Review the genuine production delta in local_search.index_status(None): a valid
explicitly maintained empty workplace corpus must remain fresh/queryable; missing
DB, schema-only storage, stale/inconsistent metadata and physical orphan documents
must never become fresh. Check the new predicate, metadata semantics, query/access
layer interaction and removal of all registered resources. No reader writes, new
schema/fields or implicit indexing. Read empty-query-correction-r9 and actual red/
green/full QA. Independently probe this edge with real SQLite and own fixtures.

Review all four smoke fixture corrections, imports/check=False/bootstrap/cleanup,
and preservation of every old condition. The user-like smoke proves Work starts
before maintenance with nonfresh search, then keeps its exact original empty/
resolve/Work conditions after explicit canonical indexing. Three other smokes
retain positive/session/security/pagination conditions. No test weakening or
production regression is acceptable. Whole fresh pytest/static/15 native/four
smokes/seven CLI receipts are r6; review them with their precise limits.

The first full source gate failed and is retained; remaining-diagnostic-r1 is a
filtered diagnostic, never qualification. Fresh complete unfiltered source and
exact consumer archive gates still belong to primary. No tag/publication/device/
connected-host/POSIX qualification is yet claimed. Do not claim warnings fixed.

Emit actual READ_ACK; final CODE GO or CODE NO-GO with precise severity/path/line/
trigger/impact/correction, RESULT and evidence limits. Only own review artifacts,
log and scratch writes; no product, Git, lifecycle, live workplace, infrastructure,
external QA or subagents. Own stdlib/SQLite probes are permitted. Primary owns
registered QA, changes and delivery. Preserve all older candidates and receipts.
