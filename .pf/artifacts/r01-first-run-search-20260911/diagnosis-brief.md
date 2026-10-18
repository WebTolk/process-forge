# R01 independent diagnosis brief

You are a bounded diagnostic shell worker. Do not edit product code, tests,
checksums, project configuration, releases, or existing audit artifacts. You
may write only the required report. Do not create subagents, commit, push,
install, restart services, or rebuild context.

Trace the disposable sequence in `tools/smoke_user_like_garage_path.py`:
`workplace-init`, `project-onboard`, then native MCP `pf.context`, `pf.search`,
`pf.resolve`, and `pf.work.start`. Determine exactly why generated
`.pf/artifacts/project-profile.md` is declared as full-text but the Garage
index reports `empty_corpus`.

Read only focused code around project package/resource construction in
`tools/processforge.py`, context local_search_resources construction, and
`src/processforge_core/{garage,local_resource_search}.py`. Compare with
`tools/smoke_garage_no_hooks_sessionless.py` and the shared fixture helper,
which register resources through the Workplace contract.

Run the existing R01 smoke once. You may create only normal system-temporary
test fixtures, never repository-root scratch folders. Report: exact causal
chain with file/function locations, whether automatic profile search is a
documented/current product contract, the smallest safe repair options, and
commands actually run. Do not propose an authorization bypass or a snapshot-
only fixture. Keep the report concise and use repository-relative paths.
