# Review: Python Core refactor Phase A worker outputs

Status: pass_with_conditions

Scope: Four `gpt-5.3-codex-spark` shell-worker tasks in run `python-core-refactor-phase-a-20260814`.

## Evidence checked independently

- All four task records pass `task-doctor`; each required report exists and all worker runs ended with exit code 0.
- `tools/processforge.py` remains a 23,482-line monolith. The reported Process-contract functions are present at the cited boundaries: catalog/resolve around lines 12,626-12,693, authoring normalization around 13,254-13,364, contract validation at 14,263, and route/handoff at 16,562-16,646.
- Runtime entrypoint delegates exist in the CLI around lines 18,456-18,504. `tools/pf_runtime` is separately organized but still loads the monolith by dynamic import in `codex_hooks.py` and `mcp_server.py`; it is not yet an independently reusable PF Core.
- Release claims in the redacted report match `RELEASE_DIRS`, `RELEASE_ROOT_FILES`, `RELEASE_PF_PUBLIC_FILES`, `RELEASE_REQUIRED_PATHS`, `release_ignore_patterns`, `release_test_commands`, `command_release_pack`, and `command_release_archive_test` in `tools/processforge.py`.
- `git diff --check` passes. Serena was available but its language server was offline, so source verification used targeted `rg` searches.

## Per-worker disposition

| Task | Result | Disposition |
| --- | --- | --- |
| `python-core-process-contract-inventory` | Contract ownership and existing seams are sufficiently evidenced for Phase A. | pass_with_conditions: synthesize call/fan-in details before extraction. |
| `python-core-adapter-runtime-inventory` | Runtime/CLI/MCP/worker inventory is useful and the main dependencies are confirmed. | pass_with_conditions: do not describe existing runtime modules as the target Core; they dynamically depend on the monolith. |
| `python-core-public-surface-inventory` | Included local absolute paths and unsupported claims about ignore/discovery behavior. | rejected; do not use as architecture evidence. |
| `python-core-public-surface-redaction` | Replacement contains only repository-relative references and its key packaging claims were checked. | pass. |

## Required next action

Use the accepted reports and the redacted public-surface report to synthesize the Phase A audit, factual dependency map, architecture alternatives, and compatibility-cleanup plan. No extraction or product-code modification is approved by this review.
