# Journal and diagnostics development delivery, 2026-10-16

Status: source independently accepted; cumulative qualification in progress. This document does not claim a completed
archive, device update or Runtime improvement. Public 1.2.0 publication is
not approved. The previously qualified installed executable remains
`61a7b74cfa7b1812641d7cef85760449dccb06be` until a new native update is verified.

The cumulative candidate adds the independently accepted
[diagnostics admission correction](../audits/diagnostics-admission-fairness-20261016.md)
and, only after its independent acceptance, the
[current-byte journal correction](../audits/process-event-journal-latency-20261016.md).
The latter uses a concrete Core owner and bounded memory-only derived IDs;
malformed history always retains the original complete parse. Earlier failed
source reviews remain evidence and do not qualify a candidate.

Qualification requires exact clean committed source and checksum, archive/core/
sidecar hashes, original extracted related checks, blocker-free native update
plan, preserved local configuration/history and backup preimages, one guarded
apply, ordinary installed CLI/stdio and original diagnostics/journal/budget
checks. Restored Runtime CPU and stacks are measured in separate quiet windows.
Fresh independent stdio does not establish actual connected-host acceptance.

The earlier installed baseline consumed 44.953125 CPU seconds during a
45.000778 s window and remained degraded. Its sampled hot path was HTTP event
ingestion and stage-obligation rebuilding. A worker's empty-obligation prototype
has unresolved freshness dependencies and is excluded from this candidate.
Any Runtime improvement must be measured after installation, not inferred
from isolated append timings.

Full accumulated release suites, 1.2.0 version/changelog/migration notes and
actual connected-host proof remain required before a detailed readiness report
and separate approval. Broad smoke inventory cleanup and device model catalog
are separate future tasks; different models may operate concurrently on a device.

Accepted journal source: `82f6bb43a310ffdd2b49ab4e1be1de244e2feacd`; diagnostics: `17206a1b335ea5d1c10ce374896cd2b3c729ffed`. Both have identical full-SHA dev readbacks.
