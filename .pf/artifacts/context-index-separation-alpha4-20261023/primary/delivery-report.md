# Alpha4 delivery report

Delivered P1 task pf-context-refresh-indexing-separation-20261019 in its approved
alpha4 scope. Project init/context refresh/repair/search observe search readiness
without building, queueing or waiting for documentation indexing. Required context,
resource authorization and CLI/MCP query contracts remain enforced.

One Core owner handles explicit workplace maintenance, existing scoped CLI
refresh/rebuild/tick, selected batch indexing and a cold future-scheduler callable.
There is no registered periodic job. SQLite FTS5 remains the workplace store at
`<workplace>/runtime/search/local-resource-search.sqlite`; a narrow backend Protocol
supports later adapters without adding an unused database abstraction or backend.

`knowledge-add-batch` uses native per-item transactions, reports partial failures,
and invokes one final indexing pass with successfully added qualified IDs only.
Unselected bodies/rows remain intact. Known covered changes can be acknowledged;
unknown/unselected changes and prior failures remain pending. Dry-run is read-only;
indexing failure preserves additions and returns a nonzero exit.

Required source failures preserve prior cache rows and report nonfresh. Durable
coordination, bounded readers, independent notifications, retryable audit delivery,
canonical root-set identity and whole observation checkpoints cover reviewed
failure/race cases. All accepted independent findings have regression evidence.
On Windows, concurrent token replacement may explicitly fail; notifications remain
durable/nonfresh and callers retry. The independent stress probe retained all 160
notifications across 20 series, with 31 safely returned publication refusals.

The requested topology is one primary, one logical independent reviewer and four
logical native contributors. The maintenance contributor also completed the user
batch steering in a bounded successor. Rejected reviews/candidates and real native
failures are retained; they were never counted as product CODE GO. Fresh actual
CODE GO applies only to source-candidate-r20.json.

Fresh whole pytest: 732 passed, 7 skipped, 246 subtests passed in 358.83s (0:05:58).
15 affected native checks and seven actual CLI invocations passed. Six SQLite
ResourceWarnings remain recorded, not suppressed or claimed fixed. Ruff passed
34 Python files and four actual changed Main functions, strict mypy 14 production
modules, Bandit ten modules with zero findings. Nine new modules: statements
95.28%, branches 91.03%; not whole
repository coverage. Actual PF-resolved Python/OOP sources and provenance were read.
Four corrected native smoke fixtures passed fresh acceptance and registered Ruff.
All 31 original guard predicates are retained, with six additional guards. A
bounded Core correction keeps an explicitly maintained empty corpus queryable,
while schema-only/stale/inconsistent state remains nonfresh. Seven new regressions
and the whole fresh suite cover it. The fresh independent review includes this
production delta. The rejected first source gate and remaining-check diagnostic are
retained; only the subsequent full unfiltered source/archive profiles qualify.

Qualified source commit: `7a8f726c320460ecfa99cd8dbf96ea8a631be00f`. Full native public source profile:
274 checks, PASS.
The exact retained archive consumer passed the full unfiltered native public
profile: 272 checks,
PASS. Both CLI entry points passed.
ZIP SHA256: `52474515eb6cbf59c7a307481a16ab717391c1616a6c924fd6d9156e8ee1aaf2`.
Sidecar SHA256: `31f2faaf99fc33823b7b66642b274ca8ac1d2c496ecb618e4beadb7c1289246c`.

Published prereleases: [GitHub](https://github.com/WebTolk/process-forge/releases/tag/v1.3.0-alpha4) and
[GitVerse](https://gitverse.ru/webtolk/process-forge/releases/tag/v1.3.0-alpha4). All four downloaded assets match
their qualified hashes and sizes. GitVerse uses `.manifest.json.txt` with identical
bytes; remove `.txt` for tools expecting the adjacent standard sidecar filename.
Tag `v1.3.0-alpha4` remains on the qualified source. Metadata commit
`171036e694f165f212256fef76af721679c3efb6` was pushed and read back on both dev remotes; the public
alpha feed selects alpha4. Prior alpha entries, alpha3 assets and stable feed are
preserved; GitHub latest stable remains v1.2.0. Foreign work remains byte-identical,
including the paused Main refactor, excluded from the source commit.

Qualification is Windows source/exact archive plus independent fixture stdio MCP.
This Work does not update the installed device or claim actual connected-host or
native POSIX acceptance. Current PF scopes must finish natively before a fresh
bounded evidence finalizer commits/pushes portable reports and reads final heads.
