# Code assurance: project SQLite journals

Result: PASS for this source slice. Primary review only; the immutable capsule forbids subagents, so no independent reviewer is claimed. Device acceptance remains separate.

## Review findings and resolution

- Unique admission and history/pending/verification updates share explicit SQL transactions. Operation-local connections always close; WAL/FULL and a busy timeout cover cooperating local writers. SQLite exceptions surface as journal failures and the CLI reports an actionable refusal rather than accepting a failed write.
- Fixed subject-only verification keys so different assignments cannot overwrite each other when history is off.
- Closed the admission-before-dispatch crash window with durable pending dispatch. A duplicate Host event now flushes that pending event too; a Runtime tick drains bounded pending work. Delivery IDs are deterministic. Cross-database/Ledger/chat effects remain recoverable, not falsely described as one transaction.
- Raw history off preserves only unfinished native input; completion removes that payload, preserving minimum IDs/hash/result. Denials and deferred capture have explicit completion behavior.
- The migrator is explicit, streaming, repeatable and non-destructive. SQL IDs/raw hashes/native keys are checked; duplicate-ID conflicts fail. Partial imports are gated. Final file signatures and source-list/hash comparison reject changes even after an earlier source was read. Skip-invalid requires an explicit flag.
- Hot ingress no longer reads canonical history or rebuilds projections. Metadata-only idle projection signatures are independent of ordinary event append; latest verification revision invalidates them. Work gates continue to check authoritative inputs independently.
- Current project consumers use SQL; workplace administrative events, diagnostics and transcripts retain their distinct existing owners. No compatibility scan or hidden full optional history was added.
- Final inventory: 69 product/docs/check paths plus the public checksum inventory. Exactly two static snapshot templates belong to a separate disjoint companion Work, with its own unchanged capsule; all other changes belong to the primary capsule. Existing unrelated private configuration, assignments and staged state are preserved.

## Test plan and cases

Use isolated data. Exercise six producer processes and retries, growth to 100000 history rows, indexed ID query plans and no Python whole-file reads; atomic rollback/reopen; pending dispatch retry/tick; raw-off pending cleanup and quarantine; project isolation; all 36 device/project override combinations and invalid reload; non-destructive repeat migration, invalid/conflict/interrupted/changing-source paths; off-history chat delivery and Work terminal recovery; existing Runtime, provider, prepared-context, continuation, doctor and diagnostics consumers.

## Retained focused results

All commands below exit 0; exact output is retained under checks/:

| Check | Evidence |
| --- | --- |
| smoke_process_event_concurrency.py | checks/event-concurrency.txt: six producers, 301 unique concurrent events, 100303 final history rows, covering unique index lookup |
| smoke_raw_ingress_incremental_recovery.py | checks/raw-recovery.txt: rollback/reopen/retry, pending cleanup, raw-off quarantine, project isolation |
| smoke_hook_sqlite_configuration.py | checks/config.txt: 36 inheritance combinations, live resolution/CRUD, last-valid reload, verification without history |
| smoke_hook_sqlite_migration.py | checks/migration.txt: dry run, invalid skip, stable IDs, originals, rerun, conflict, import interruption and source-change rejection |
| smoke_hook_sqlite_runtime.py | checks/runtime-off-history.txt: no hot scan/rebuild, live independent overrides, actual chat delivery, duplicate pending dispatch recovery, idle cache and off-history Work completion recovery |
| validate-process-forge-schemas.py --root <isolated-source> | checks/source-schemas.txt |
| validate-public-cleanliness.py --root <isolated-source> | checks/source-cleanliness.txt |
| validate-process-forge-checksums.py --root <isolated-source> --check | checks/source-checksums.txt |

Broader existing checks also passed in this session: smoke_workplace_configuration, smoke_central_event_ingress_kernel (six raw processes), smoke_central_event_ingress (CLI + temporary Runtime), smoke_central_event_replay, smoke_provider_adapter_admission, smoke_runtime_host_poc, smoke_runtime_metrics, smoke_automation_readiness (20 cases), smoke_codex_lifecycle_identity, smoke_first_run, smoke_stage_projectors, smoke_prepared_execution_context, smoke_work_completion_recovery (all before/after terminal-write interruptions and malformed intents), smoke_process_run_task_batch, smoke_long_lived_runtime, smoke_runtime_status_timeout, smoke_conversation_completeness, smoke_continuation_work, smoke_remediation_doctor_contracts and smoke_diagnostics. Changed Python syntax, both logging schemas and git diff --check passed.

## Isolation and limitations

The dirty workspace-wide schema validator found a preexisting old assignment execution_mode string; public-cleanliness found preexisting local docs.python package bindings in the private working manifest. This task did not edit either. Therefore the authoritative source checks use HEAD plus only the 69 owned public changes in an isolated tree, with the committed manifest. Both full source validators pass there. The checksum inventory was regenerated there and compared entry-by-entry: no unrelated path was changed by inventory regeneration.

Tests used current Windows Python 3.14.3 and SQLite 3.50.4. The concurrency timing in the retained output measures this busy machine, not a capacity promise. No million/tens-of-millions dataset or new remote/server database was claimed.

Installed Core, actual running Runtime, actual connected MCP and real device journal migration were not changed or qualified. Old NDJSON must be frozen during an operator-controlled cutover; the migrator does not stop old writers. Chat transcript storage remains its existing NDJSON owner, including its existing per-message read behavior. Optional UI detail levels/new provider adapters and a general asynchronous processing engine are outside this slice.

## Final product paths

- `docs/authoring/workplace-configuration.md`
- `docs/concepts/chat-relay.md`
- `docs/concepts/hook-journal-sqlite.md`
- `docs/concepts/hooks-events.md`
- `docs/concepts/process-events.md`
- `docs/concepts/processforge-events.md`
- `docs/concepts/resource-events.md`
- `docs/concepts/runs-tasks-iterations.md`
- `docs/concepts/runtime-mcp.md`
- `docs/concepts/runtime-model.md`
- `docs/concepts/session-telemetry.md`
- `docs/getting-started.md`
- `docs/known-limitations.md`
- `docs/ru/concepts/chat-relay.md`
- `docs/ru/concepts/hooks-events.md`
- `docs/ru/concepts/process-events.md`
- `docs/ru/concepts/runtime-mcp.md`
- `docs/ru/concepts/runtime-model.md`
- `docs/ru/known-limitations.md`
- `schemas/project-configuration.schema.json`
- `schemas/workplace-configuration.schema.json`
- `src/processforge_core/composition.py`
- `src/processforge_core/configuration/__init__.py`
- `src/processforge_core/configuration/models.py`
- `src/processforge_core/configuration/resolution.py`
- `src/processforge_core/configuration/service.py`
- `src/processforge_core/configuration/storage.py`
- `src/processforge_core/configuration/yaml_store.py`
- `src/processforge_core/process_event_journal.py`
- `src/processforge_core/project/snapshot_rendering.py`
- `src/processforge_core/raw_hook_journal.py`
- `src/processforge_core/sqlite_storage.py`
- `src/processforge_core/work/automation_readiness.py`
- `src/processforge_core/work/cancellation_replay.py`
- `src/processforge_core/work/continuation.py`
- `templates/project-context.snapshot.md`
- `templates/project-context.snapshot.yaml`
- `templates/workplace-configuration.yaml`
- `tools/migrate-hook-journals.py`
- `tools/pf_cli/application.py`
- `tools/pf_cli/commands/configuration.py`
- `tools/pf_cli/parsers/configuration.py`
- `tools/pf_runtime/host.py`
- `tools/pf_runtime/raw_ingress_kernel.py`
- `tools/pf_runtime/service.py`
- `tools/pf_runtime/session_replay.py`
- `tools/process_execution_smoke_support.py`
- `tools/processforge.py`
- `tools/smoke_automation_readiness.py`
- `tools/smoke_central_event_ingress.py`
- `tools/smoke_central_event_ingress_kernel.py`
- `tools/smoke_central_event_replay.py`
- `tools/smoke_codex_lifecycle_identity.py`
- `tools/smoke_conversation_completeness.py`
- `tools/smoke_diagnostics.py`
- `tools/smoke_first_run.py`
- `tools/smoke_hook_sqlite_configuration.py`
- `tools/smoke_hook_sqlite_migration.py`
- `tools/smoke_hook_sqlite_runtime.py`
- `tools/smoke_hook_sqlite_support.py`
- `tools/smoke_prepared_execution_context.py`
- `tools/smoke_process_event_concurrency.py`
- `tools/smoke_process_run_task_batch.py`
- `tools/smoke_raw_ingress_incremental_recovery.py`
- `tools/smoke_remediation_doctor_contracts.py`
- `tools/smoke_runtime_host_poc.py`
- `tools/smoke_runtime_status_timeout.py`
- `tools/smoke_work_completion_recovery.py`
- `tools/validate-process-forge-schemas.py`
