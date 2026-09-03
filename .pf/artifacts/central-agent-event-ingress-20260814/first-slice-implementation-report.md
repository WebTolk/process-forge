# Central Agent Event Ingress: first-slice implementation report

Date: 2026-08-15
Owner: main orchestrator (after the approved shell-worker writers produced no accepted source diff)

## Delivered

- Added `tools/pf_runtime/raw_ingress_kernel.py`: provider-neutral native envelope, canonical raw identity, stable-native-ID conflict identity, private hourly NDJSON journal, atomic indexes, explicit stale-lock recovery, recovery of missing indexes, and poisoned/collision quarantine.
- `host.ingest_event` now writes the raw receipt before running the pre-existing normalized project path. Legacy normalized Runtime input is wrapped into a generic `processforge` envelope; provider adapters can send native envelopes with an optional derived event.
- `codex_hooks.py` is a thin adapter: it owns the Codex SessionStart/SessionEnd/PostToolUse mapping and legacy normalized inputs, while all hooks with a project `cwd` (including unknown hooks) are sent as raw envelopes.
- Runtime `/event` and the direct Codex fallback both call `host.ingest_event`, therefore use the same durable raw ingress path.
- Removed an unused, unimported worker residue `central_event_ingress.py`; it duplicated storage and placed Codex-specific mapping in a core-like module.

## Behaviour and safety properties

- Raw persistence happens before normalized project routing. A project/session denial still returns the established error/HTTP 403, but leaves the private raw fact for audit.
- A duplicate raw event is not appended again. It nevertheless retries the derived project effect, which repairs an effect missing after a simulated crash.
- A reused stable native ID with changed raw content is quarantined as `native_id_payload_conflict`.
- Paths are contained below `<workplace>/runtime/agent-events`; payload size and JSON-key validity are enforced; index replacement is atomic; lock recovery is explicit and does not automatically remove a live local lock.
- No automatic chat projection was added. There is no accepted provider-content contract in this first slice, so `chat_message_ids` stays empty and raw journal data remains private.

## Validation

All commands passed on Windows:

- `python tools/smoke_central_event_ingress_kernel.py` — duplicate, native-ID poison conflict, missing-index recovery, invalid/oversize payload, containment, stale lock and 16-process append.
- `python tools/smoke_central_event_ingress.py` — Codex mappings, Runtime/fallback raw-id equivalence, unknown-hook raw-only capture, missing-only derived repair, project/session mismatch raw audit, and privacy.
- `python tools/smoke_runtime_ledger_hooks_mcp.py` — existing Ledger/Codex/MCP compatibility.
- `python tools/smoke_long_lived_runtime.py` — long-lived daemon duplicate and cross-project HTTP behaviour.
- `python tools/smoke_processforge_core_package_bootstrap.py` — package-root bootstrap.
- `python -m py_compile ...` for changed runtime and smoke modules; `git diff --check`.

`release-pack` was also invoked for a separate `.pf/tmp` validation archive, but correctly refused before writing because the repository has pre-existing and current uncommitted files. Thus archive inspection is a delivery gate still pending a clean/committed worktree, not a failed product test.

## Residual scope

This is the reviewed first implementation slice. It does not add providers, UI, automatic chat content projection, or a user-facing replay command. Raw duplicate delivery already provides missing-only derived repair and missing-index recovery. A later slice can add operator replay tooling against the stored receipt/index contract.
