# Supervisor observation of captured attempts

Automatic supervisor ticks used to repeat a full collection for completed
attempts whose governed parent Work was still active. That reread current
sources, resource selections and output bodies before reaching the existing
completion marker. The installed private development baseline still consumed
95.066% of one CPU core over 45 seconds; overlapping stack samples located
293 of 540 samples in supervisor/collection. This source change alone does
not establish an installed Runtime improvement.

The accepted policy distinguishes historical capture from fresh collection.
`CapturedAttemptReader` checks current bounded private metadata: exact
project/run/assignment/context/attempt, prepared byte seal and input fingerprint,
capsule byte/contract/intent pins, receipt fingerprint and matching completion.
It uses existing Core path, digest, fingerprint, YAML and metadata readers,
without calling the CLI or Runtime. The caller holds the existing lifecycle
lock. No parsed document or authorization cache is introduced.

Both completed-attempt supervisor paths report an established capture in
`historical_observed` and `observed`, leaving `collected` for full collection.
The same proof removes that attempt from collection drain. Missing, malformed,
inconsistent or unreadable proof takes the original collection path. Historical
observation neither reads current output/source bodies nor asserts current
access, fresh acceptance or parent completion. Explicit collect, first capture
and interruption recovery retain the original full checks and their order.

Five alternating ordinary pairs on the same isolated fixture with four real
completed governed attempts measured supervisor wall medians of 3.874953 s
before and 0.521741 s after; CPU medians were 3.578125 s and 0.421875 s.
Both paths performed real report/event writes. Assignment, run, capsule,
prepared-input, receipt, completion and worker-state bytes stayed unchanged.
The baseline function came from sealed pre-edit source with identical surrounding
implementation. Profiling was separate; the installed baseline Runtime remained
active during these timings. These are source fixture measurements.

Existing recovery coverage now checks both supervisor branches, historical
observation after source/output changes versus explicit collect rejection,
metadata tamper, identity/attempt/pin mismatch, read denial, missing completion
and drain recovery. The existing prepared-context and supervisor failure checks
also pass. Independent review, clean archive, installation, actual Runtime and
connected-host acceptance are separate evidence layers. The broad smoke audit
and global launcher model policy remain separate tasks. Public 1.2.0 publication
requires the detailed readiness report and explicit approval.
