# R01 execution record

Primary reproduced the previous `empty_corpus` result and traced it to the
intentional boundary between a project snapshot and the shared Workplace index.
`src/processforge_core/local_resource_search.py` defines the physical index as
Workplace-owned; `tools/processforge.py:workplace_search_runtime_snapshot()`
uses registered Workplace package manifests only; `garage.py` uses the project
snapshot as query authorization and for `pf.resolve`.

The old first-run smoke incorrectly expected a generated project-local profile
to be physically indexed. The repaired test proves the actual contract: empty
fresh search, project-context profile resolution, and governed work start.
`docs/concepts/garage-core.md` records that distinction for operators.

PF shell worker `r01-contract-diagnosis` was started on gpt-5.6-luna/high after
its capsule was deliberately renewed following the plan tool's context refresh.
It was cancelled after exceeding the bounded diagnostic interval without a
report; its runtime state and stderr are preserved under `.pf/runtime/agent-runs`
and it made no source edits. Primary completed the focused reproduction and
review. This is a worker infrastructure failure, not a successful delegation.

Validation PASS:

- `python tools/smoke_user_like_garage_path.py`
- `python tools/smoke_garage_no_hooks_sessionless.py`
- `python tools/smoke_project_init_local_search_mcp.py`
- `python tools/validate-process-forge-checksums.py --root . --write`
- scoped `git diff --check`.
