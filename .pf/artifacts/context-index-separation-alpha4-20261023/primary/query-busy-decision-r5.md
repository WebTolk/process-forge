# Bounded refusal for a writer arriving between status and SQL

The unchanged operational-hardening smoke next reproduced a real low-level query
race: the read-only status was fresh, then a writer obtained SQLite's exclusive
lock before the query's SQL read. Zero busy timeout correctly avoided waiting but
the old query path raised search_unavailable. A deterministic real SQLite test
failed at both the backend and project-service layers before the correction.

Only SQLITE_BUSY/SQLITE_LOCKED (including their extended codes) now produce the
existing empty degraded response shape with portable search_database_busy reason.
No sleep, retry, write connection or implicit maintenance is introduced. Invalid
queries and other released exceptions retain their prior mapping. Connections
still close in finally. The project response projects the actual degraded query
state into its readiness, rather than attaching a preceding ready observation.
Both deterministic cases pass under the existing 1.5-second nonwaiting bound.

The latest preceding whole regression was 646 passed, 7 environment skips and
202 subtests, with six retained SQLite ResourceWarnings. Final r10 source QA and
unchanged native hardening/search/containment checks must pass before the fresh
independent review. No public release readiness is claimed at this checkpoint.
