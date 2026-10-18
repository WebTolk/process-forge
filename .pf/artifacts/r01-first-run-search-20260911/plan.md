# R01 plan

The first-run project profile is a selected project-context resource. It is
resolvable through `pf.resolve`, but it does not enter the single physical
Workplace index: that index is built only from registered Workplace packages and
the project snapshot is only a query-time authorization filter.

The old `smoke_user_like_garage_path` expected profile text in `pf.search` and
therefore contradicted the established index architecture. The smallest repair
is to make the scenario prove the actual no-infrastructure first-run contract:

1. `pf.context` is Garage and reports an empty, fresh corpus;
2. `pf.search` returns no documents without treating that state as an error;
3. `pf.resolve` still returns the selected project profile; and
4. `pf.work.start` starts governed work.

Add an explicit documentation paragraph distinguishing project-context
resolution from the shared Workplace corpus. No search authorization, SQLite
indexing, package registry or project-profile production code changes are
needed. This conclusion is independently supported by comments in
`local_resource_search.py`, `garage.py`, `session_read.py`, and the previous
baseline reproduction. The bounded worker was cancelled after it exceeded the
diagnostic limit with no report; its state/log remain preserved.
