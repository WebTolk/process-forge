# Release Blocker Validation

Дата: 2026-08-23

## Status

Implemented and locally validated.

## Checks Run

- PASS: `python -m py_compile tools/processforge.py tools/pf_runtime/session_read.py tools/smoke_context_freshness_vs_execution_readiness.py`
- PASS: `python -m py_compile tools/processforge.py tools/pf_runtime/mcp_server.py tools/pf_runtime/session_read.py tools/smoke_context_freshness_vs_execution_readiness.py`
- PASS: `python tools/smoke_context_freshness_vs_execution_readiness.py`
- PASS: real Joomla MCP acceptance against `D:\.agents\processforge-workplace`
- PASS: `python tools/smoke_project_context_freshness_policies.py`
- PASS: `python tools/smoke_project_init_local_search_mcp.py`
- PASS: `python tools/smoke_resource_indexing_policy_acceptance.py`
- PASS: `python tools/smoke_project_init_acceptance.py`
- PASS: `python tools/smoke_project_classification_data_driven.py`
- PASS: `python tools/validate-process-forge-schemas.py --root .`
- PASS: `python tools/validate-public-cleanliness.py --root .`
- PASS: `python tools/validate-process-forge-checksums.py --root . --write`
- PASS: `python tools/validate-process-forge-checksums.py --root . --check`
- PASS: `python tools/processforge.py release-check --root .`
- PASS: `python tools/processforge.py doctor-project --project-root .`
- PASS: `python tools/processforge.py events-validate --project-root .`
- PASS: `git diff --check`
- PARTIAL: `python tools/processforge.py release-test --root . --public --fail-fast --timeout-scale 1`
  - All target freshness/MCP/search/resource/init smokes passed.
  - Stale named release ZIP/manifest artifacts were removed from `dist/`; the public dist check then passed.
  - The remaining failure before commit was `smoke_release_manifest_provenance_contract`, because `release-pack` correctly refuses to publish from a dirty Git source.
- PASS: `python tools/processforge.py release-test --root . --public --fail-fast --timeout-scale 1` from committed clean source, with unrelated pre-existing projection/report dirt temporarily removed from the worktree.

## Acceptance Mapping

- Freshness and execution readiness separated: PASS.
- Missing execution capability does not make resources stale: PASS.
- `pf.session_context` shows both states: PASS.
- `pf.search` works with fresh resources and blocked execution: PASS.
- `pf.resolve` works for resolved resources: PASS.
- Platform requirement was not converted into a provider: PASS.
- Cross-project/session boundary remains enforced by existing MCP session/project checks: unchanged, covered by existing `smoke_project_init_local_search_mcp.py`.
- Stale `pf.resolve` fails closed: PASS, covered by `smoke_context_freshness_vs_execution_readiness.py`.
- Workplace capability providers are recognized without turning platform requirements into providers: PASS.

## Release Source State

`release-pack` provenance requires a clean Git checkout. The clean-source
public release-test passed after the slice was committed, with unrelated
pre-existing dirty projection/report files kept out of the release source.
