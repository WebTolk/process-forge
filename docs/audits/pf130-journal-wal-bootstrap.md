# Concurrent cold journal WAL activation

This correction supports the journal performance work for 1.3.0. Concurrent
workers can reach a newly initialized event or raw hook journal before WAL is
enabled. SQLite can return SQLITE_BUSY from the journal-mode change immediately,
even when a native busy timeout is configured. The previous adapter refused the
operation at that point.

The adapter now retries only that pre-publication WAL activation statement.
Every attempted cursor is closed before waiting. One monotonic budget comes from
the connection's existing busy_timeout; subsequent native waits receive the
remaining budget. The original timeout is restored before domain publication or
connection disposal. Only primary SQLITE_BUSY is retried. Other errors,
exhausted budgets and a returned mode other than WAL refuse the operation.

The existing already-WAL fast path, FULL synchronization, header checks,
migration barrier, owner admission and read-only behavior remain. Schema creation,
BEGIN, domain writes, event dispatch and caller bodies are never replayed.

## Verification

The changed source is qualified with the existing bootstrap suite plus four
regressions. Both real Windows and Linux execute all nine cases without skips:

- A separate process holds an actual reserved writer on a valid DELETE-mode
  journal. It commits after the contender observes real SQLITE_BUSY. Both event
  and raw APIs preserve the seed and holder data and publish one new record.
- Real contention across zero and 60 ms budgets refuses without publication.
  Timeout restoration and attempted cursor closure are checked.
- Nonbusy, missing-code and SQLITE_LOCKED errors are classification guards.
  An actual in-memory non-WAL result is refused.
- Existing initialization interleaves, foreign/partial headers, unknown schema,
  read-only access and migration barriers retain their tests.

The unchanged six-producer smoke covers 301 unique concurrent admissions,
deduplication, 100000 historical rows, indexed lookup, rollback and dispatch
recovery. Successful native Windows and Ubuntu CI results for the final commit
are delivery requirements.

Local Linux smoke failures are retained alongside the passing focused tests.
A diagnostic trace showed continuous successful publications while competing
writers exhausted the configured ten-second admission timeout under slow FULL
commits. The correction does not promise writer fairness, replay transactions,
or extend timeouts to make a workload pass. Native Linux CI must qualify the
complete scenario before merge.

SQLite's [busy handler documentation](https://sqlite.org/c3ref/busy_handler.html)
explains that lock promotion can bypass the handler. Its
[journal_mode contract](https://sqlite.org/pragma.html#pragma_journal_mode)
requires callers to check the actual returned mode. This change introduces no
schema, backend, global lock or database consolidation.
