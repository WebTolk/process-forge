# T03 independent code review

Scope reviewed: `work_context.py` and the focused Work/process execution and CLI consumers for intent normalization, identity, pinning, immutable sources, no-overwrite, stage separation, and capsule reuse. Review was source-only; no tests or live services were run by this reviewer. Serena Python symbols were unavailable, so inspection used scoped UTF-8 reads/searches.

## Findings and current status

- **Resolved — run identity could be fabricated from `run_id` alone.** The builder now requires `_run_matches` to find the assignment in the exact run and match process identity before emitting `identity.kind: work` (`work_context.py:291-293, 314-324, 364-376`). Missing/nonmember runs produce assignment identity plus an explicit readiness blocker. The validator checks Work membership and compares its process pin (`:451-457`).
- **Resolved — a corrupt existing run pin could fall through to the live catalog.** The current builder distinguishes an absent pin on a legacy run (one-time new-context capture, tagged `capture_origin`) from a present malformed pin, which returns no pin and leaves the context blocked (`work_context.py:314-336`).
- **Resolved — conflicting checksum declarations for the same required source could be silently collapsed.** `_capture_sources` now retains and diagnoses conflicts (`work_context.py:255-286`), so a required-source checksum cannot be discarded by declaration order.
- **Resolved — schema-known intent could change without changing the intent digest.** `input_artifacts` now join required sources, and schema-known obligations are projected into immutable intent (`work_context.py:133, 177-195`).
- **Resolved — malformed execution-mode and subagent values could normalize permissively.** Execution mode values and permission flags are type/enum checked (`work_context.py:108-129`); subagent flags, limits, roles, and report paths are checked (`:90-100`).
- **Resolved — a governed capsule could be edited and semantically revalidated during worker preparation.** The common validator checks the assignment's recorded path and raw capsule checksum, then confirms the parsed supplied object is the exact pinned bytes (`work_context.py:415-427`). Process lifecycle state also checks its raw-byte pin before semantic validation (`process_execution.py:1334-1352`).
- **Resolved — malformed `identity.kind` was not rejected.** The validator now accepts only `work` or `assignment` (`work_context.py:445-447`), and `require_ready` refuses non-Work identity (`:488-490`).

No unresolved blocking source finding remained in the reviewed paths after the latest fixes. No-overwrite uses exclusive creation and rejects existing capsules including force requests; immutable source checks enforce project-relative paths, symlink/special-file exclusion, stable reads, per-file and aggregate limits, and byte checksums. Stage view remains derived separately from pinned process definition and current assignment stage, outside immutable intent.

This is a source review verdict only. Parent-owned parity, schema, workspace, and regression checks are separate and were not independently rerun here.
