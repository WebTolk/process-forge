# Final Validation

Run: `operational-hardening-search-update-20260822`

## Commands

```text
python -m py_compile src/processforge_core/local_resource_search.py src/processforge_core/core_update.py tools/processforge.py tools/smoke_search_update_operational_hardening.py tools/smoke_core_update_manifest.py
python tools/smoke_search_update_operational_hardening.py
python tools/smoke_project_init_local_search_mcp.py
python tools/smoke_core_update_manifest.py
```

Additional release/checksum validation is required after checksum inventory refresh.

## Status

pass_with_conditions

## Results

- Python compile: pass.
- Search operational smoke: pass.
- MCP local search smoke: pass.
- Core updater smoke: pass.
- Checksum inventory: pass.
- Checksum/release surface parity: pass, 861 release-pack entries excluding the inventory itself.
- Public cleanliness: pass.
- ProcessForge schema validation: pass.
- `git diff --check`: pass.

## Incidental Cleanup

Schema validation exposed pre-existing `.pf/assignments/*` records where
`result.status` used `blocked`, while the schema only allows
`pending|done|failed|cancelled`. Those records kept their assignment-level
`status: blocked`; only `result.status` was normalized to `failed`.

## Conditions

- Live Codex host `/hooks` and `/mcp` proof was not executed from this repository-only context.
- Real OS locked-handle smoke and Runtime daemon stop/start integration remain future slices.
