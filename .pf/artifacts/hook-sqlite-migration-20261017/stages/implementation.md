# Implementation: project hook/event SQLite journals

Status: ready for code assurance. Exact run garage-hook-sqlite-implementation-20261017-migrate-project-hook-event-jo; implementation capsule unchanged.

User-authorized migration replaces full NDJSON scans with project-local transactional owners and indexed reads. PFConfig adds independent raw_hooks/events device defaults and nullable project overrides; resolution is live and immutable. Minimal admission, pending delivery/native input and latest verification facts remain operational when history is off. Runtime no longer rebuilds projections on ingress and skips unchanged periodic stage builds. Explicit temporary migrator streams old files, preserves IDs/originals, gates partial imports and validates sources/counts/integrity.

Changed source, configuration, schema, documentation and necessary integration checks are listed below. All paths are inside the current immutable capsule. No installed Core, actual service lifecycle, host hooks or MCP reconnection was changed. No subagents were used (capsule forbids delegation). Existing unrelated .pf and staged state preserved.

Preliminary focused validations passed; code-assurance will retain repeatable command evidence and review residual issues. Initial service.py dirty flag had no content diff before this task; the resulting three-line functional change belongs to this task.

- `docs/authoring/workplace-configuration.md`
- `docs/concepts/hook-journal-sqlite.md`
- `docs/concepts/hooks-events.md`
- `docs/concepts/process-events.md`
- `docs/concepts/runtime-model.md`
- `docs/ru/concepts/hooks-events.md`
- `docs/ru/concepts/process-events.md`
- `docs/ru/concepts/runtime-model.md`
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
