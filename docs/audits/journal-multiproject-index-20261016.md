# Per-journal process-event snapshots — 2026-10-16

Status: source implementation ready for independent review. No package, installed
Runtime, connected-host or public 1.2.0 qualification is implied.

## Ownership and freshness

`src/processforge_core/process_event_journal.py` retains one latest immutable
snapshot per admitted routing key, in the existing concrete owner. Up to 64 slots
share the existing 16,777,216-byte budget. Fixed-size lexical path hashes route
lookups; collisions and aliases can reduce reuse. Every lookup still reads all
current bytes and computes SHA-256. Reuse also requires matching size, reader
identity, parser policy and sufficient stack headroom. Paths, mtime and routing
tokens never prove freshness or confer access.

New routes may evict the least recently used slot. An admitted journal replaces
its own generation without evicting neighbours. Charged tombstones remember
routes after budget denial, including repeated append-copy denials. The slot cap
and aggregate budget also bound these records.

## Memory and concurrency

One nonblocking optional-operation lease bounds builders and borrowed snapshots
to one operation. Contended calls execute the mandatory full scan without
allocating another index or waiting for optional capacity. A short metadata lock
protects admission, reservations, invalidation and publication. An append
invalidates its route before the mandatory write; another in-flight operation
cannot publish after that invalidation. There is no retired-generation queue.
Metadata references are cleared on exceptional exits and before lease release.

Reservations cover backing dictionaries, strings/ordinals, failed rows, list
growth, tuple freeze, append-copy containers, indices, policies, digests, keys,
slots and bookkeeping. Values include 16-byte alignment plus a per-object
allowance. Dict growth reserves old and new tables before insertion. Capacity
bounds use CPython 3.10–3.14 layouts with at most 64-bit pointers; other admitted
interpreter families/versions fall back to scanning. This work exercised 3.14.3.
The 32,768-byte owner allowance and 8,192-byte slot allowances are conservative;
32 KiB reservation batches never cause additional eviction.

On the real corpus with two 100-row neighbours, retained accounting was
15,546,068 bytes and the maximum reservation was 15,578,092 bytes. This is an
index-metadata limit, excluding mandatory raw/decode buffers, caller-owned and
stdlib object graphs, allocator arenas and overall RSS. Large copy/growth peaks
may be refused, causing later reparsing; optional memory is never awaited.

## Compatibility and checks

Public constructor/contains/append signatures and imports are preserved. The
parser/serializer recognition, policy comparison, ID helper, depth helper and
suffix scan retain their original AST. Ordered failed-row replay, blank-line
differences, first-match stopping, consumed-row suffix fallback and refusal to
publish partial cold matches remain covered. Mandatory read, reader, guard,
serialization, write, flush, fsync and hook failures retain their boundaries.
Optional metadata failures reduce reuse.

The unchanged `tools/smoke_process_event_concurrency.py` passed through a
sandbox-compatible fixture-directory adapter. Direct TemporaryDirectory setup
was denied before assertions. The adapter uses ordinary mkdir and retains the
fixture; no test assertions, source or ACLs were changed.

Task-local controls passed: interleave isolation; 30 append generations;
same-size/mtime edits and delete/create; aggregate and bad-row budget denial;
160 routes bounded to 64; 12 repeated copy-peak denials preserving a neighbour;
eight contended readers and same/other-journal append barriers; late publication;
13 optional fault sites; mandatory failures and uncertain-write retry;
history-reader MemoryError and traceback cleanup; forced routing collision;
real-corpus object-size/reservation checks. The module imports without CLI/Host.

## Measurements

Five ordinary before/after pairs per sequence, alternating version order, with a
new owner per sequence and the first cold-index call included. A/B each contain
4,096 rows and 278,528 bytes; R contains 101,379,731 bytes. The same absent ID
forces complete scans. SHA seals are checked after every call, outside timing.
The Runtime remained active; OS cache was not cleared. CPU has coarse resolution
on short calls. These are source comparisons, not quiet installed measurements.

Medians of three-call totals:

| Sequence | Wall before, ms | Wall after, ms | CPU before, ms | CPU after, ms |
|---|---:|---:|---:|---:|
| AAA | 15.078 | 25.547 | 15.625 | 15.625 |
| ABA | 48.839 | 38.009 | 46.875 | 31.250 |
| RRR | 1943.804 | 1668.376 | 1890.625 | 1609.375 |
| RAR | 2800.976 | 1629.528 | 2765.625 | 1578.125 |

Separate sys.setprofile counts, without replacing json.loads:

| Sequence | JSON before | JSON after |
|---|---|---|
| AAA | 4096/0/0 | 4096/0/0 |
| ABA | 4096/4096/4096 | 4096/4096/0 |
| RRR | 78107/0/0 | 78107/0/0 |
| RAR | 78107/4096/78107 | 78107/4096/0 |

Every call performed exactly one full read: 278,528 bytes for A/B or 101,379,731
for R, before and after. The returning R call in RAR had median wall
1371.197 → 139.651 ms. Single-journal cold-inclusive
measurements and their overhead remain visible in the table; interleave gains
do not establish whole-Runtime CPU improvement or faster every-call behaviour.

Source before: `7ada76ac787b9a322a429a87306d3352005e040cc2768b38793ac99779b5470c`.

Source after: `cc1febbe34c4c5161c6d37e04823aca6fc275f978456e7b1394e9a44315ac62d`.

Protected R SHA-256: `4a16fb136990aa98dead88aafacbea0841ac0980d439564dbc06e6021dcb921d`. It was neither copied to disk nor
appended, and its seal stayed unchanged. All observed lookups returned False.

## Architectural acceptance and remaining gates

The change follows D01/D02/D05/D06/D07/D09/D11 and
R04/R06/R07/R08/R10/R11/R12: concrete Core infrastructure ownership, current
reads, no grants from cache, preserved journal durability and error boundaries,
one writer, portable public reporting and no new transport/legacy dependency.
Other Work/process rules are untouched. No framework, DI engine or second
production implementation was introduced.

Evidence includes ordinary pair arrays, separate counts, targeted controls,
source seals and the review diff. Independent review, archive/package checks,
private dev delivery/install and Runtime/connected-host profiling remain with the
primary operator. Public 1.2.0 still requires a detailed report and explicit
approval. This audit does not close the OOP programme or qualify deployment.
