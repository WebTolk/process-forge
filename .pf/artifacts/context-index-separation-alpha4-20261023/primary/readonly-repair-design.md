# Bounded repair: genuinely read-only index observation

Native observation analysis identified a race in local_search.index_status: after
is_file succeeds, sqlite3.connect(path) may recreate a removed database and waits
the default busy timeout. The same unguarded reader connection exists in search.
authorized_coverage already uses a read-only URI but has the default timeout.
Index writes/build/dirty operations must keep their existing writable connections.

Authorize a separate primary-owned scoped Work over local_search.py and one focused
test file, with own artifacts/log/scratch, to change only read connections and
their bounded error mapping. Use SQLite mode=ro URIs, timeout=0, preserve live WAL
semantics and current schema/status/errors, never immutable/nolock shortcuts.
On removal/locking/unavailable metadata, report degraded/unavailable rather than
creating files or waiting. Preserve query and resource-ID filters unchanged.

Characterization: reproduce disappearance between is_file and connect on an owned
fixture; hold a real exclusive SQLite lock and measure bounded refusal; verify
normal fresh queries/coverage plus Unicode/#/? URI paths and no database creation.
Check WAL behavior separately if supported, without claiming arbitrary untested
backends. Registered pytest/Ruff/format/mypy and focused existing smokes apply.
The independent aggregate reviewer must review this repair together with all
native contributions. No new infrastructure, database engine or project grants.
