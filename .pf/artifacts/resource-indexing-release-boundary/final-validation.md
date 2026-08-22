# Final Validation

Status: in_progress

## Passed So Far

- `python -m py_compile tools/processforge.py src/processforge_core/local_resource_search.py tools/pf_runtime/mcp_server.py tools/pf_runtime/session_read.py tools/smoke_project_init_local_search_mcp.py tools/smoke_search_update_operational_hardening.py tools/smoke_resource_indexing_policy_acceptance.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/validate-process-forge-checksums.py --root . --check`
- `python tools/smoke_resource_indexing_policy_acceptance.py`
- `python tools/smoke_search_update_operational_hardening.py`
- `python tools/smoke_project_init_local_search_mcp.py`
- `python tools/smoke_evolve_privacy_sanitizer.py`
- `python tools/smoke_evolve_targeting_privacy_sanitizer.py`
- `python tools/processforge.py release-check --root .`

## Pending

- Source commit/push.
- Release archive build from clean source.
- Extracted quick/full archive validation.
