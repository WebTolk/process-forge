# SQL database foundation

`processforge_core.database` is a synchronous, cold SQL API. Import, construction
and `DatabaseFactory.from_profile` do not connect, create directories or initialize
storage. SQLite is the only closed driver mapping. Repository SQL uses SQLite
syntax and `?` bound values; there is no SQL portability claim.

Host composition resolves profiles relative to the actual flow root, validates
containment including symlinks/reparse points, and supplies an authorized absolute
`DatabaseTarget`. The default project profile is nonpersisted `data/pf.sqlite3`.
A profile grants no filesystem access. The factory checks structural settings and
scope; it cannot infer the missing base to repeat containment checks. Bindings pin
the path and concrete store identity; config reload must not retarget an existing
execution binding. Workplace storage is not activated by this slice.

`Database.read()` opens an existing read-only store and a snapshot. `transaction()`
opens an existing read/write store with `BEGIN IMMEDIATE`. Success commits; any
`BaseException`, including a failed commit, rolls back and closes. Neither operation
creates a missing store or retries. Sessions and streams are operation/thread-bound;
rows and write results are detached values. Exit the stream context on early stop.
Batch sizes are 1–1000; execute-many accepts at most 10000 rows and no statement
parameters. Values are finite SQLite scalars, excluding bool and integers outside
signed int64. Duplicate row column names are rejected.

Deadlines are absolute `time.monotonic()` values. SQLite busy waits use the smaller
of the configured timeout and remaining budget; a progress handler interrupts long
queries. `DatabaseError` exposes only a stable code and retryability. A transaction
must never span process spawning/waiting, signals, output/projection I/O, backup or
full scans.

`SchemaManager.inspect()` does not create storage and may discover a concrete store
using an expected `store_id=None` while still checking owner/scope/application id.
The wildcard cannot authorize normal reads or writes. Explicit `initialize()`
requires an absent path and concrete UUID hex identity. A failed initialization
retains a blocked uninitialized target for explicit maintenance, without fallback.
`apply()` adds absent code-owned namespaces atomically with checksum registration;
same version/checksum is a no-op, upgrades/drift/future schemas refuse. The digest
is SHA256 of UTF-8 canonical JSON `{namespace,version,statements}`, sorted keys,
compact separators, no ASCII escaping, no NaN or trailing newline, prefixed
`sha256:`. Envelope application id is `0x50464D31`, user version is 1.

WAL is established/verified during explicit administration. Writes verify FULL
synchronous durability and foreign keys. Public sessions deny administrative
SQLite opcodes; they are repository DML/query interfaces, not an untrusted SQL
sandbox. Physical identity is verified before domain access. Legacy accounting,
events and hooks retain their current databases and factories.

Configuration optionally accepts `database: {profiles: {...}, defaults: {...}}`.
Each profile has `scope`, `driver: sqlite`, relative `path`, and optional exact-int
`timeout_ms` (0–30000, default 100). IDs match `[a-z][a-z0-9_-]{0,63}`. Unknown keys,
unsafe/expanding paths and invalid defaults refuse. Maps are immutable. Project
overrides permit project profiles/project_main only and cannot collide with inherited
names. An absent section remains absent in old serialization and config operations.


## Native transport and application selection

`DatabaseFactory.resolve_driver(config=None)` is a cold closed sqlite mapping.
`SQLiteDriver._connect(database, *, timeout=5.0, isolation_level='', uri=False)`
is the internal native transport seam: it forwards caller options unchanged,
returns a native connection and leaves native exceptions/lifetime to the adapter.
It performs no PRAGMA, BEGIN, mkdir, identity adoption or migration. Main `_admin`
uses this seam while retaining its stronger envelope/error/deadline checks.
Legacy adapters use it through their own injected driver; their domains and paths
stay separate from main. Cross-owner adapters are integrated separately.

`STORE_ENVELOPE_DDL` exports the two existing code-owned statements unchanged for
recognized-store additive identity migration. Main UUID/scope/owner/application ID
and namespace checks are unchanged; normal access never accepts legacy as main.
Only SchemaManager.inspect permits a noncreating expected UUID wildcard.

`DatabaseConfig.driver` selects sqlite independently of profiles; absent/null uses
the builtin. Get full effective settings through ConfigurationProvider, then
resolve_driver(snapshot.config.database); never rediscover configuration in a
transport adapter. A driver/profile grants no target permission. Binding and
containment remain host responsibilities; refresh cannot hot-switch a pinned DB.
