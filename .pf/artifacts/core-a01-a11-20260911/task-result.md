# A01-A11 implementation result

Date: 2026-09-11. Owner: primary. Status: accepted for run review.

| Task | Final behavior | Focused regression |
| --- | --- | --- |
| A01 | File-root search authorizes only that file; directory discovery remains contained. | smoke_search_file_root_containment |
| A02 | Output validation, worker preparation, collection, host authorization and task fingerprint resolve report paths before reads. | smoke_expected_report_containment |
| A03 | Bad project cache, missing assignments and failed ticks do not silently kill the scheduler or stop healthy projects. | smoke_runtime_scheduler_failure_isolation |
| A04 | Status preserves degradation and reports scheduler liveness; recovery restores health. | smoke_runtime_scheduler_failure_isolation |
| A05 | Bad migration archive sources block planning; apply faults leave structured failure and durable partial recovery records. | smoke_core_update_migration_sources |
| A06 | Authenticated reports retain diagnostic paths after strict identity/content/hash checks; secrets and forged envelopes remain rejected. | smoke_authenticated_report_content |
| A07 | Exact session identity has collision-resistant storage; old presence/chat history remains compatible without duplicate active projections. | smoke_session_identity_roundtrip |
| A08 | Native MCP validates JSON-RPC and tool schemas before dispatch; notifications stay silent. | smoke_mcp_jsonrpc_validation |
| A09 | Equivalent classifier distributions produce equal semantic context identity; content changes still invalidate it. | smoke_classifier_distribution_parity |
| A10 | Singleton operations share an OS guard, refuse live/ambiguous owners and permit dead-owner recovery. | smoke_runtime_singleton_orphan |
| A11 | Startup/resume remain distinct lifecycle facts; identical delivery is idempotent. | smoke_codex_lifecycle_identity |

Independent review added root-aware search identity/freshness and portable
resolution-failure coverage (`smoke_search_multiple_roots`). All 11 new scripts
have current PASS and original-baseline failure records. Four review findings
are resolved in `review-disposition.md`; no blocking implementation task remains.

Primary registered the tests, updated English/Russian runtime/session/MCP docs,
refreshed checksums and adapted old live-owner/single-session fixtures to the
repaired behavior. No external dependency was added. Full-suite outcome, exact
changed-file hashes and final process status belong to run review/summary.
Acceptance is source-only; installed application and release are outside scope.
