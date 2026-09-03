# Changelog Source Audit

Date: 2026-08-23

## Sources

- Git range reviewed: `v1.0.2..HEAD` at intake.
- Current `CHANGELOG.md` before this run had no `1.1.0` section.
- Release-test list confirms coverage for Runtime, MCP/session, local search,
  update manifests, freshness/readiness, archive provenance, and extracted
  archive validation.
- Prior committed artifacts and smoke names confirm the listed product changes:
  session read layer, event capture/replay, project init local search MCP,
  search maintenance, core update recovery, resource indexing policy, and
  freshness/readiness split.

## CHANGELOG Mapping

- `Added / MCP session tools`: backed by `pf.session_context`,
  `pf.session_chat`, `pf.session_activity` implementation and smokes.
- `Added / local resource search`: backed by `smoke_project_init_local_search_mcp`,
  `smoke_resource_indexing_policy_acceptance`, and search-index commands.
- `Added / Runtime event capture and replay`: backed by Runtime host/replay
  smokes and long-lived runtime smoke.
- `Added / manifest core update`: backed by `smoke_core_update_manifest` and
  `smoke_update_stage_verify_apply_file_provider`.
- `Changed / maintenance-owned search refresh`: backed by updated project-init
  and resource-indexing smokes.
- `Changed / freshness vs execution readiness`: backed by
  `smoke_context_freshness_vs_execution_readiness`.
- `Internal / ResourceSearchIndex`: backed by this run's refactor in
  `src/processforge_core/local_resource_search.py`.

## Exclusions

The changelog intentionally excludes worker IDs, temporary paths, `.pf/artifacts`
paths, private orchestration details, and commit hashes.
