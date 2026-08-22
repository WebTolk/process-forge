# Resource Indexing Release Boundary Log

## 2026-08-22 21:30 - codex-main

Task: Bootstrap `.pf` run/task/capsule for resource indexing release boundary.
Files changed: `.pf/runs/resource-indexing-release-boundary-20260822/run.yaml`, `.pf/assignments/resource-indexing-release-boundary-main.yaml`, `.pf/contexts/assignment-capsules/resource-indexing-release-boundary-main.capsule.yaml`.
Artifacts changed: project context snapshot refreshed; resource indexing run created.
Templates used: ProcessForge run/task/capsule commands.
Tools used: `python bin/pf.py project-context-check`, `project-context-refresh`, `run-create`, `task-create`, `assignment-capsule`, `task-start`.
Decisions: Use `--force-with-handoff` for legacy active assignment scope overlaps; keep this work in its own artifact directory.
Risks: `project-context-refresh` printed `STATUS: fresh` but returned code 1 once; follow-up `project-context-check --json` confirmed fresh snapshot.
Next steps: Implement resource-oriented indexing and release-boundary reports.
Handoff: none.

## 2026-08-22 22:15 - codex-main

Task: Implement declarative indexing and resource-owned search index.
Files changed: `src/processforge_core/local_resource_search.py`, `tools/processforge.py`, `tools/pf_runtime/session_read.py`, schemas, docs, smokes.
Artifacts changed: `.pf/artifacts/resource-indexing-release-boundary/*.md`, `.pf/reviews/resource-indexing-release-boundary/*.md`.
Templates used: assignment expected output list.
Tools used: `py_compile`, `validate-process-forge-schemas`, search/MCP/privacy smokes, checksum validator, release-check.
Decisions: Use derived DB schema v3 and rebuild-on-schema-mismatch; keep `index_policy` only as legacy compatibility; make `pf.search` return stale/missing/degraded status without query-time refresh.
Risks: Real Joomla core source snapshot root `D:\.agents\docs\Joomla-core` was absent, so production corpus benchmark is blocked in this environment.
Next steps: Commit source/report state, build release archive from clean Git source, validate extracted archive.
Handoff: source commit required before `release-pack`.

## 2026-08-22 22:09 - codex-main

Task: Fix `release-pack` clean-source blocker exposed by `.pf` runtime projections.
Files changed: `tools/processforge.py`, `checksums/processforge.sha256`, `.pf/artifacts/projections/*`.
Artifacts changed: runtime projection snapshots refreshed.
Templates used: release-delivery acceptance constraints.
Tools used: `py_compile`, direct helper assertion, checksum writer, `release-pack --dry-run`.
Decisions: Keep Git provenance strict for source, but allow only modified `.pf/artifacts/projections/command-history.md` and `stage-obligations.json`, which are runtime-generated and excluded from the release archive.
Risks: Any non-projection dirty path, deletion, or untracked file remains a release-pack blocker.
Next steps: Commit the fix, build the release archive, validate extracted archive.
Handoff: none.

Update: Root cause was `git_release_output()` using `.strip()`, which removed the leading porcelain status space from ` M .pf/...`; changed it to strip only trailing newlines before the final archive attempt.

Update: A second `release-pack` attempt passed provenance and exposed ZIP/manifest ordering drift because generated `processforge-core.manifest.json` was appended after sorted source files; fixed `write_release_zip()` to sort source and generated entries together.

Update: `release-archive-test --root` then exposed that freshness comparison knew only physical root files; changed it to recompute the generated core manifest hash from the root release set and sidecar provenance.

## 2026-08-22 22:24 - codex-main

Task: Build and validate resource-indexing release archive.
Files changed: `dist/processforge-1.0.2-resource-indexing-20260822.zip`, `dist/processforge-1.0.2-resource-indexing-20260822.manifest.json`, final `.pf/artifacts/resource-indexing-release-boundary/*.md`.
Artifacts changed: final validation, archive correction, qualification reports.
Templates used: release-delivery acceptance constraints.
Tools used: `release-pack`, `release-archive-test --extracted-test quick`, extracted `smoke_resource_indexing_policy_acceptance.py`, extracted `smoke_project_init_local_search_mcp.py`, process inspection for full-gate blocker.
Decisions: Treat quick archive validation plus targeted extracted resource-indexing/MCP smokes as release proof for this boundary; classify full public release-test hang in long-lived runtime as separate blocker.
Risks: Full extracted public release-test was interrupted after several minutes in `smoke_long_lived_runtime.py` / `runtime project-state`; orphan child processes were stopped.
Next steps: Commit and push final archive/report/projection state.
Handoff: none.
