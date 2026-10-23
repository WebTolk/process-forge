# Frozen implementation architecture and ownership

Applies D01/D02 shared Core, D03 cold construction, D04 explicit factories,
D05 operation lifetimes, D06 current access, D07 durable recovery, D09 Python-native
composition and D11 bounded migration. D08 registration and D10 new transports are
unchanged. R01-R12 are preserved: exact identity, no stage override/capsule edits,
current access, no new grants, live reads, durable failures, no provider trust
changes, role separation, one writer, retry identity and private-path redaction.

Canonical interfaces (freeze before workers):

* resources/index_observation.py: maintenance_state_path(workplace_root: Path)
  returns workplace/runtime/search/maintenance-state.json. IndexObservationService
  (workplace_root: Path, *, distribution_root: Path | None = None).observe()
  returns current physical index status using the existing catalogue/index with
  verify_files=False; it does not enumerate/read document contents, create files,
  mark dirty, build, queue or wait. Surface durable running/failed state truthfully;
  interrupted running is incomplete until authorized maintenance recovers it.
  No private paths in new public diagnostics. Worker 1 also owns resources/access.py:
  remove all hidden maintenance from readiness/search and use observation while
  retaining payload shape, snapshot guards, selected-resource coverage and filters.
* resources/index_maintenance.py: WorkplaceIndexMaintenanceService(workplace_root:
  Path, *, distribution_root: Path | None = None).run(*, reason: str = 'manual',
  verify_files: bool = True) -> dict[str, Any]. Reuse catalogue and existing index
  maintenance_tick; return existing schema1 pf.search_index.maintenance payload
  with scope/workplace, project_count=0, results, report. Serialize all new global
  clients across processes, persist running/complete/failure atomically, retry on
  next pass after interruption. No Main callbacks or Runtime imports. OS-backed
  lock or SQLite writer lease must be nonblocking/bounded and crash-releasing;
  preserve existing index atomicity. No install or global side effects in fixtures.
  New thin commands/search_maintenance.py WorkplaceIndexMaintenanceCommand.execute
  adapts explicit --workplace, --apply, optional --json. Parser in matching file
  registers new top-level search-index-maintain. Existing commands/options unchanged.
  Manual success 0; missing apply or maintenance failure nonzero with safe reason.
  New operation schema_version=1/kind above, no MCP schema changes. Calling the
  explicit command is workplace operation; a project Work never authorizes it.
* resources/index_schedule.py: IndexMaintenanceSchedule(workplace_root: Path, *,
  distribution_root: Path | None = None, period_seconds: float = 300.0,
  retry_seconds: float = 30.0), run_due() -> dict[str, Any]. Cold construction,
  monotonic timing, immediate first pass, no catch-up flood, retry bounded, call
  the canonical maintenance service, report safe job state. Injectable narrow
  clock/maintenance ports are allowed for tests. Worker 3 owns Runtime service.py:
  separate search maintenance loop/thread with stop_event and independent observable
  scheduler.jobs.search_index state; no project routing or session as prerequisite.
  Shutdown joins owned thread; failure isolates from project scheduler/metrics.
* Primary: Main adapter integration. Refresh/init/repair observe readiness, never
  call maintenance. Keep public keys including search_index with truthful observed
  payload and maintenance-style printable summary. Register manual adapter and
  make existing workplace mutation calls delegate to the canonical service.
  Version, checksums, release notes, source preservation, QA and publication owned
  by primary. No four-worker writes to Main/composition/version/release/checksums.

Native 1-1-4 ownership (separate scoped Works, not parent preparation tasks):
1 observation: index_observation.py, access.py, tests/context_index_separation/test_observation.py.
2 maintenance: index_maintenance.py, tools/pf_cli/{commands,parsers}/search_maintenance.py,
  tests/context_index_separation/test_maintenance.py.
3 scheduling: index_schedule.py, tools/pf_runtime/service.py,
  tests/context_index_separation/test_schedule.py.
4 integration (starts after implementation): tests/context_index_separation/test_integration.py,
  conftest.py, relevant existing search/MCP/scheduler smoke adjustments, four EN/RU
  context/search concept docs. Meaningful source/fixture/CLI/MCP parity tests,
  first/repeat refresh with absent/stale/running index and unavailable App Server,
  large registry instrumented read counts/timing, no project access widening.

Each owns separate task report/log/tmp. Primary must not write a worker's files
while its native attempt is active. Fourth worker starts after 1-3 and primary
integration; independent reviewer starts after all implementation. Reviewer writes
only own report/tests in own scratch. No self-review or fabricated READ_ACK.

Python: constructor injection and narrow Protocol, immutable configuration/value
records where appropriate; no universal core:Any port, god object or new container.
Explicit small factories win over adding dependency merely for this bounded slice.
Existing unmodified monolith bridges remain recorded residuals, never claimed fixed.
