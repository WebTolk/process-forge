# Investigation and impact

Baseline 9cd730a9. Serena read exact Main command_project_context_refresh,
search_index_maintenance_for_known_projects and RuntimeProcess.scheduler_loop;
scoped source reads inspected ResourceSearchService and ResourceSearchIndex.

Observed call graph: project refresh -> workplace catalogue -> maintenance_tick
-> index_status(verify_files=True) -> full document fingerprint map and possible
build/rebuild. Project initialization and repair also call global maintenance.
More seriously, ResourceSearchService._readiness and search silently call the
same maintenance, so merely reading pf.context or searching may build the index.
Existing ResourceSearchIndex is already resource-oriented; project snapshots are
query-time authorization. Reuse it, WorkplaceSearchCatalogReader, SQLite and atomic
publication, rather than introducing a second index engine or permission model.

Runtime has separate scheduler/metrics threads but no search maintenance job.
Its scheduler owns project ticks, Ledger/Director/Inspector and temporary-file
observation. Search must have an independent thread so a large documentation pass
cannot stall project ticks, requests, context refresh or metrics. No live service
operation is part of this implementation. Registered Python QA tools are activated
and their shared toolchain/registry commands have been read; no dependencies added.

Impact: Main refresh/init/repair become observations; resource search/readiness
become read-only; existing search/index storage and access filtering stay canonical.
A small workplace maintenance owner adds serialization, durable state, retry and
an explicit manual adapter. Existing resource-management call sites delegate to it.
Legacy search-index scoped commands retain parameters/results. Tests requiring
implicit indexing must explicitly maintain an isolated fixture first. Baseline
behavior is intentional change under the selected task, not refactor parity.
Before/after timing and file-read counts will be recorded by worker 4 on fixtures;
no current live indexing performance or connected-host reload is claimed.
