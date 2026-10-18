# Process-event journal latency, 2026-10-16

Status: v5 source independently accepted after structural JR-02/JR-03 correction. Archive,
installed execution, shared Runtime CPU and the actual connected host require
separate qualification. Earlier rejected variants do not qualify this source.

A genuine installed Work-admission profile attributed 9.839 instrumented seconds
to four event publications, including repeated decoding of historical JSON.
The concrete Core `ProcessEventJournal` now owns append/deduplication; its legacy
wrapper retains preparation outside the registry SystemExit adapter, the same
cross-process writer guard and post-lock hook dispatch. Serialized bytes,
ordered early duplicates, JSONDecodeError-only suppression, flush/fsync and
mandatory failures keep their existing boundaries. CLI remains an adapter;
the broader OOP migration is still incomplete.

One bounded private memory-only ID index may represent an exactly scanned body.
Every append still reads all current bytes and hashes them under the original
guard; exact digest, size, canonical reader and supported current parsing policy
are required. Retained strings/set storage are limited to 16 MiB. There is no
disk sidecar, TTL, metadata-only freshness or omitted current read. Cold/changed
history, unstable UUID fallback, unknown configured parser behavior, optional
allocation failure and exceeded limits retain full ordered parsing.

V5 never indexes a body containing a suppressed JSONDecodeError. Error classes,
constructors and descriptors are not inspected at module import or trusted for
reuse. A suppressed error while parsing the appended record also prevents index
publication. This deliberately trades cache hits for the old failure behavior.
The fixed 101,379,731-byte real-history corpus contains 78,107 dictionary rows
and one malformed row, so this corpus uses the full-parse fallback rather than
the warm ID index. It must not be presented as a warm-index speed measurement.

Earlier independent reviews found optional allocation refusal (JR-01), mutable
parser/error behavior bypass (JR-02) and optional error-metadata import failure
(JR-03). Their FAIL reports and exact old seals remain historical. The v5
original smoke passed unwrapped in 3.905492 s, including four actual writers,
same-size/restored-mtime changes, external append/truncate/delete, byte/error/
durability/hook boundaries, optional allocation failure, parser limits,
configured callbacks and constructor descriptors, and preimport error aliases.
Fifteen prefix cases with five requests per version retain identical output.
Earlier transition-event/central-replay checks passed; final archive checks
remain cumulative delivery work. Independent review is separate from primary
execution; no review capture is claimed to be a READ_ACK.

Five alternating serial four-event pairs use the same sealed corpus, native
guard/fsync and dispatch=False, including the first cold request. There is no
profiler or count wrapper in timed windows. All output hashes and final source
seals match. Wall medians: 9.515165 s before and
7.753035 s after; CPU medians: 8.812500 s before and
6.859375 s after. The installed older shared Runtime remained active.
These are paired append batches, not actual Work creation or Runtime CPU proof.
The earlier v4 2.881292 s median belongs to rejected code and is not acceptance.

Full byte I/O remains linear and this malformed corpus still parses in full.
Objective-catalog admission and Runtime stage-obligation projections are separate
unrepaired paths. Cumulative archive/install/profiling and full release suites
remain required. Public 1.2.0 requires a detailed ready-candidate report and
separate user approval. Broad smoke inventory cleanup remains a future task.
