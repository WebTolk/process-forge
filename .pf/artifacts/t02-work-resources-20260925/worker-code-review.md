# T02 independent code review

Date: 2026-09-26
Reviewer: bounded independent source review
Scope: `work_resources.py`, `work_resource_material.py`, and focused Work resource integration in `process_execution.py`, `garage.py`, `local_resource_search.py`, `tools/processforge.py`, and `tools/pf_runtime/mcp_server.py`.

## Verdict

No remaining confirmed security or correctness blocker found in the reviewed paths. Exact run/assignment/context selection is enforced before resource access; the capsule checksum, membership, process and snapshot pins are checked; stage scope and fresh project grants narrow access before current material is read; material paths are checked for containment and symlink traversal; search uses a per-request in-memory FTS database.

Primary identified an accounting gap for generated metadata summaries and total ephemeral document text and informed the reviewer. The reviewer checked the repair: the current implementation tracks document count and UTF-8 document bytes in the shared request budget (`work_resource_material.py:26-27, 48-80, 442, 480`). This attribution was clarified by primary integration before acceptance.

## SQLite connection follow-up

Confirmed regression: `authorized_coverage` and `WorkResourceService._search` previously relied on `sqlite3.Connection` context managers, which commit or roll back but do not close the connection. Both functions now explicitly close in `finally` blocks (`local_resource_search.py:523-531`; `work_resources.py:264-273`). The supplied `connection-verification.json` reports PASS, and `verify-connections.py` checks closure after successful use and failures, including Windows temporary-directory cleanup without forced garbage collection. This fixes the finding in the reviewed code. The primary reports the final full regression is still pending.

## Review limits

This was a source-only review. Serena could not parse Python in this session (`Active languages: []`), so I used the authorized scoped UTF-8 source fallback. I did not run tests, live services, installed-Core checks, or release checks. A possible pin-consistency concern was checked against the actual persisted assignment shape and dismissed: the assignment pin intentionally stores the process and snapshot identity plus capsule path/checksum, while selected resource IDs and the full definition are pinned in the run and capsule.
