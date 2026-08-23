# ProcessForge 1.1.0 Scope Freeze

Date: 2026-08-23
Status: frozen

## Allowed Until Release

- Release blockers.
- Security or data-loss fixes.
- Regressions in existing behavior.
- Packaging, update, checksum, and archive-validation fixes.
- Documentation and tests that describe or validate existing behavior.
- Behavior-preserving Python refactor with characterization coverage.

## Deferred

New product capabilities, new public workflows, new MCP tools, new file formats,
and semantic changes to process/runtime/search/update behavior are deferred to a
post-1.1.0 backlog.

## Active Slice

The only allowed refactor slice in this run is a local-resource-search service
extraction around existing `src/processforge_core/local_resource_search.py`
behavior. Compatibility function APIs remain available.

## Known Start Boundary

The run started with generated `.pf` projection drift and a stale/broken
project-context snapshot.

Root-cause analysis showed that the snapshot builder implicitly selected the
first `processes[]` catalog entry as the execution route when scalar `process:`
was empty. That made enabled process definitions behave as active execution
selection and produced a false release blocker. The allowed release-blocker fix
removes that fallback and adds a regression smoke proving that `processes[]`
remains a catalog while explicit `process:` still activates process capability
requirements.

After the fix, `project-context-refresh` and `project-context-check` report a
fresh/ready context and the assignment capsule was generated.
