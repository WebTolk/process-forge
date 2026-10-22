# Verified source map and impact

2026-10-22. Read-only source inspection using Serena; shell fallback for exact non-code documentation/fixtures and filenames. No provider was invoked and no real agent session was launched. This is planning evidence, not runtime qualification of accounting.

| Existing surface | Verified fact | Design consequence |
| --- | --- | --- |
| `tools/codex_exec_worker.py::main` | Runs `codex exec`, selects configured model, writes final response via `-o`, subprocess exit and heartbeat; no structured usage capture in the inspected wrapper. | Extend the driver collector in a future implementation; output report text and requested model are insufficient usage/billing evidence. Qualify supported structured output against installed CLI/version first. |
| `tools/prepared_executor.py::main` | Prepared manifest validates exact worker identity; heartbeat carries started/finished timestamps and process status. | Reuse verified run/task/attempt binding and attempt elapsed-time facts; preserve current output/exit contracts. Add monotonic elapsed measurement where needed; do not derive model usage from heartbeat. |
| `tools/pf_runtime/codex_hooks.py::native_envelope` and `codex_adapters.py` | Raw-first session/event normalization and provenance checks; input/output messages are not request usage. Stable hook delivery ID is not assumed. | Shared ingress and binding patterns are useful; an additional qualified source collector is needed for tokens. Interactive agent accounting cannot be assumed to work just because hooks are present. |
| `tools/pf_runtime/kimi_hooks.py::normalized_event`, `native_envelope`, `kimi_adapters.py` | Preserves `token_count` / `estimated_token_count` as event data; hooks and schema validation have no normalized accounting contract. Fixture uses those fields on PreCompact/PostCompact. | Context size/estimate must not contribute to spend. See primary-source check below. |
| `src/processforge_core/process_event_journal.py` and `sqlite_storage.py` | Existing SQLite transaction/admission/index patterns and event IDs. Project journal also supports history-disabled mode; ordinary duplicate handling does not always compare conflicting payload hashes. | Reuse storage primitives where contracts fit, not lifecycle journal tables or ordinary duplicate semantics as the accounting ledger. Accounting needs durable contribution/revision/conflict rules independent of optional event-history logging. |
| `docs/concepts/agent-ledger.md` | Ledger is workplace attendance/presence/lease layer, distinct from raw ingress and work verification. | Heartbeat/session duration is not agent execution time. Accounting is a separate capability, with explicit bindings and coverage. |
| `tools/pf_runtime/monitor.py::collect_snapshot` | Bounded local Runtime state/readiness snapshot with infrastructure metrics; no accounting application queries. | Reuse presentation/terminal ideas later. Query accounting directly through a shared read service; do not make Runtime monitor state a second accounting source of truth. |
| `docs/concepts/domain-neutral-core.md`; `.pf/artifacts/pf-framework-architecture-20261005/domain.md` | Pure rules separated from providers, storage and transports; shared admission/provenance/Work identity; no universal Core façade or implied microservices. | A small neutral accounting module with provider adapters and common queries fits existing boundaries. |

Searches for normalized input/output/cached/reasoning usage in the inspected `src` and `tools/pf_runtime` surfaces found no existing accounting implementation. This is a bounded source observation, not a claim that no external host/export can supply usage.

## Primary-source check requested by the operator

Google/web search followed by official documentation and upstream source, accessed 2026-10-22:

- [Kimi hook reference](https://moonshotai.github.io/kimi-cli/en/customization/hooks.html) associates `token_count` with PreCompact and `estimated_token_count` with PostCompact. These are not a hook usage receipt.
- [KimiSoul source](https://github.com/MoonshotAI/kimi-cli/blob/main/src/kimi_cli/soul/kimisoul.py): PreCompact uses current context token count; ordinary step completion publishes `result.usage` in StatusUpdate. Compaction has a separate call/result path and telemetry. Therefore coverage of compaction, retries and subagents must be tested separately, not inferred from ordinary step capture.
- [CompactionResult source](https://github.com/MoonshotAI/kimi-cli/blob/main/src/kimi_cli/soul/compaction.py): post-compaction context size combines available summary output usage with a text-length estimate for preserved messages; it remains a context-size estimate.
- [Wire StatusUpdate source](https://github.com/MoonshotAI/kimi-cli/blob/main/src/kimi_cli/wire/types.py) defines nullable current-step `token_usage` and `message_id` separately from context size. Null fields mean no status change, not zero usage.
- [TokenUsage source](https://github.com/MoonshotAI/kimi-cli/blob/main/packages/kosong/src/kosong/chat_provider/__init__.py) defines disjoint `input_other`, `input_cache_read`, `input_cache_creation`; total input is their sum, total usage adds output. No separate reasoning count is established by this schema.
- [Wire mode reference](https://moonshotai.github.io/kimi-cli/en/customization/wire-mode.html) documents structured communication for external programs. Candidate collector: supported version of Wire or equivalent recorded native events. This is a design candidate, not an installed-source qualification or authorization to change the host.

Upstream main/docs may differ from the installed Kimi implementation. First implementation gate must pin actual client/version, obtain scrubbed real receipts, prove per-step identity and replay, and account for compaction/retries/child agents. Do not assume all Kimi variants expose this Python/Wire schema. No private transcript directories were traversed for this plan.

## Impact and limits

Future write areas: a neutral `processforge_core.accounting` package; selected provider driver/host collectors; thin CLI/MCP query bindings; task report projection; focused fixtures/tests/docs. Workplace storage configuration/path ownership and explicit project/Work binding require review before source edits. Current task changes only planning artifacts/log, original card input reference and native PF planning-cycle records.

No product API, worker exit semantics, Work transitions, Ledger identity or Monitor behavior changes in this cycle. Local documentation consulted first; external lookup was restricted to official Kimi docs and upstream code. Prices, Codex plugin APIs and installed real usage capability remain implementation qualifications, with no tariff amounts promised.
