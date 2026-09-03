# Session Replay Slice Design

## Цель slice

Минимальный session-scoped replay должен закрыть только один разрыв: после durable raw append восстановить отсутствующий project-side эффект для уже принятого raw v1 Codex-события.

Slice не должен добавлять:
- chat projection или автоматическую запись transcript;
- новых provider-адаптеров;
- широкий derived-index;
- публичные CLI-команды или изменение пользовательского Runtime API;
- перенос Codex mapping из adapter layer в Host/Core.

## Текущая опора в коде

Raw source of truth уже есть в `tools/pf_runtime/raw_ingress_kernel.py`:

- `NativeAgentEvent`
- `RawReceipt`
- `RawIngressKernel.ingest()`
- `RawIngressKernel._raw_record()`
- `RawIngressKernel._recover_indexes()`
- `raw_event_id()`
- `raw_payload_hash()`
- `stable_native_identity_key()`
- `deterministic_derived_key()`
- `contained_path()`
- `atomic_write_json()`

Текущий project-effect путь уже есть в `tools/pf_runtime/host.py`:

- `ingest_event()`
- `_ingest_derived_event()`
- `normalize_event()`
- `stable_event_id()`
- `event_exists()`
- `ledger_from_event()`
- `rebuild_projection()`
- `rebuild_stage_obligations()`
- `resolve_project()`
- `route_project()`
- `state_lock()`
- `read_json()`
- `write_json()`

Codex derived mapping boundary уже находится в `tools/pf_runtime/codex_hooks.py`:

- `EVENTS`
- `normalized_event()`
- `native_envelope()`
- `dispatch()`

Replay slice должен использовать `codex_hooks.normalized_event(raw_payload)` для Codex raw records. Нельзя заново кодировать mapping `SessionStart` / `SessionEnd` / `PostToolUse` внутри replay.

## Proposed Internal Slice

Добавить внутренний replay-компонент без public CLI, предпочтительно в `tools/pf_runtime/host.py` или в узком private-модуле `tools/pf_runtime/session_replay.py`, который вызывается только из host/runtime-internal tests.

Минимальная функция:

```python
def replay_session_raw_records(
    workplace_root: Path,
    core: Any,
    *,
    session_id: str,
    project_ref: str,
    provider: str = "codex",
    adapter: str = "codex-hooks",
    limit: int | None = None,
) -> dict[str, Any]:
    ...
```

Поведение:

1. Resolve project once через `resolve_project(project_ref, core)`.
2. Читать только raw v1 journal под:
   `runtime/agent-events/raw/v1/**/*.ndjson`.
3. Фильтровать записи:
   - `schema_version == 1`;
   - `provider == "codex"`;
   - `adapter == "codex-hooks"`;
   - `source_session_id == session_id`;
   - `source_project_ref` resolves to the same `project_root`.
4. Обрабатывать записи в порядке `(shard path, byte offset)`.
5. Для каждой записи брать `raw_payload`.
6. Получать derived event только через `codex_hooks.normalized_event(raw_payload)`.
7. Если mapping отсутствует, пометить запись как `unsupported_mapping` и не применять project effects.
8. Для mapped event вычислить текущий legacy event id через существующий путь:
   - `derived["event_id"]` оставляет Codex legacy id;
   - `stable_event_id(derived)` даст тот же `evt_<sha256>`, что и текущий Host.
9. Перед repair проверить `event_exists(project_root, stable_event_id(derived), core)`.
10. Если event уже есть, не вызывать `_ingest_derived_event()`.
11. Если event отсутствует, вызвать `_ingest_derived_event(derived, workplace_root, core, project_ref=str(project_root))`.
12. Checkpoint продвигать только после успешного `present`, `repaired`, `unsupported_mapping` или quarantined/denied result.

## Checkpoint

Checkpoint должен быть private runtime state, atomic, session-scoped:

`runtime/agent-events/checkpoints/session-replay/{safe_session_id}.json`

Писать через `atomic_write_json(path, payload, RawIngressKernel(workplace_root).root)` или эквивалентный confined atomic replace.

Минимальный payload:

```json
{
  "schema_version": 1,
  "kind": "session-replay-checkpoint",
  "processor_id": "processforge.session-replay.codex-hooks",
  "processor_version": "1",
  "provider": "codex",
  "adapter": "codex-hooks",
  "source_session_id": "<session_id>",
  "source_project_ref": "<project_ref>",
  "last_raw_event_id": "<raw_event_id>",
  "last_raw_location": "raw/v1/YYYY/MM/DD/HH.ndjson:<offset>",
  "updated_at": "<core.now_utc()>",
  "counts": {
    "seen": 0,
    "present": 0,
    "repaired": 0,
    "unsupported_mapping": 0,
    "denied": 0,
    "failed": 0
  }
}
```

Checkpoint is not a derived index. It records replay progress only.

## Failure Rules

- If raw record is malformed JSON, stop and report `failed`; do not advance checkpoint past that record.
- If `source_project_ref` cannot resolve to the requested project, mark `denied` for that record and do not call `_ingest_derived_event()`.
- If `codex_hooks.normalized_event()` returns `None`, mark `unsupported_mapping`; no project effects.
- If `event_exists()` is true, mark `present`; no Host repair call.
- If `_ingest_derived_event()` succeeds, mark `repaired`.
- If `_ingest_derived_event()` raises `PermissionError` or `SystemExit` because session/project routing is unsafe, stop before advancing past that record. That keeps later replay able to repair after routing state is restored.

## Explicit Exclusions

This slice deliberately does not implement:
- chat message replay;
- deterministic chat ids;
- chat projection;
- provider-neutral replay planner;
- provider/time/raw-id range replay API;
- derived content-conflict quarantine;
- public `pf runtime replay` command;
- new normalized event schema;
- new Ledger idempotency table.

Those belong to later broader replay/idempotency work, not this session repair slice.

## Focused Tests

1. `test_session_replay_reads_only_matching_raw_v1_records`
   - Create raw v1 NDJSON records for two sessions and two projects.
   - Replay one session/project.
   - Assert only matching Codex records are considered.

2. `test_session_replay_preserves_codex_mapping_boundary`
   - Use a Codex hook payload.
   - Assert replay calls `codex_hooks.normalized_event()`.
   - Assert replay does not duplicate `EVENTS` mapping locally.

3. `test_session_replay_skips_existing_project_event`
   - Raw record maps to a derived event.
   - Stub `event_exists()` to return true.
   - Assert `_ingest_derived_event()` is not called.
   - Assert result is `present`.

4. `test_session_replay_repairs_missing_project_event_through_host_path`
   - Stub `event_exists()` to return false.
   - Assert `_ingest_derived_event(derived, workplace_root, core, project_ref=str(project_root))` is called.
   - Assert result is `repaired`.

5. `test_session_replay_checkpoint_advances_atomically_after_success`
   - Replay two records.
   - Make the second repair fail.
   - Assert checkpoint points only to the first completed raw location.

6. `test_session_replay_unsupported_codex_payload_does_not_route`
   - Raw payload lacks required Codex fields so `normalized_event()` returns `None`.
   - Assert no `_ingest_derived_event()` call.
   - Assert checkpoint may advance with `unsupported_mapping`.

7. `test_session_replay_cross_project_record_is_denied`
   - Raw record `source_project_ref` resolves to a different project than requested.
   - Assert no Host repair call.
   - Assert result includes `denied`.

8. `test_session_replay_does_not_create_chat_or_public_cli_surface`
   - Static/import-level assertion that the slice adds no chat transcript writes and no argparse command registration.

## Acceptance

The smallest acceptable implementation is an internal session replay function plus tests. It reads existing raw v1 records, keeps Codex normalization in `codex_hooks.normalized_event()`, checks existing project events with `event_exists()`, repairs only missing project effects through `_ingest_derived_event()`, and writes one atomic session checkpoint.
