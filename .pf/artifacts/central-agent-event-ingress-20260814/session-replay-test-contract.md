# Session Replay Test Contract
`central-ingress-session-replay-test-contract-20260815`

## Источник контракта
Используются только наблюдаемые утверждения из существующего временного smoke-потока и принятый дизайн среза `session-replay-slice-design.md`.

## Реиспользуемые временные smoke-хелперы (без редизайна)
- `pf(*args: str, expect: int = 0) -> str`
- `save(path: Path, payload: dict) -> Path`
- `native_event(project: Path, session: str, hook: str, payload: dict, derived: dict | None) -> dict`
- `derived(project: Path, session: str, event_type: str, event_id: str) -> dict`
- `existing_runtime_event_id(event_id: str) -> str`
- `raw_records(workplace: Path) -> list[dict]`

## Тестовый контракт (точечные требования)

1) Фильтрация по скоупу replay (session/project)
- При запуске replay по `session_id + project_ref` обрабатываются только raw-записи:
  - `schema_version == 1`
  - `provider == "codex"`
  - `adapter == "codex-hooks"`
  - `source_session_id == <session_id>`
  - `source_project_ref` разрешается в тот же `project_root`
- Должны игнорироваться записи других сессий/проектов (проверка по отдельному тесту: `test_session_replay_reads_only_matching_raw_v1_records`).

2) Путь `present` (дубликат уже существует)
- Для каждого mapped события, если `event_exists(...)` истинно:
  - не вызывается `_ingest_derived_event(...)`
  - статус записи в checkpoint должен быть `present`
  - см. наблюдение по дублированию Host-приёмника:
    - повторная подача одного и того же события должна возвращать `deduplicated == True` и `accepted == True`
    - после crash-реплики: `deduplicated == True` и `duplicate == False` в ответе повторной отправки.

3) Путь `repaired` (в проекте событие отсутствует)
- Для mapped события, когда `event_exists(...) == False`:
  - вызывается `_ingest_derived_event(derived, workplace_root, core, project_ref=str(project_root))`
  - статус checkpoint/результата: `repaired`
- Наблюдаемое поведение Host:
  - из первого smoke: успешный первичный ingest возвращает accepted и корректный `event_id`;
  - повторный ingest после удаления эффекта project event должен дать `deduplicated == True` и `duplicate == False` без роста raw count.

4) Путь `unsupported_mapping`
- Если `codex_hooks.normalized_event(raw_payload) is None`:
  - проектный эффект не выполняется (`_ingest_derived_event` не вызывается)
  - статус: `unsupported_mapping`
  - checkpoint должен продвигаться после такого сырого события (без ошибки).
- Подтверждение из дизайн-логики: отдельный тест `test_session_replay_unsupported_codex_payload_does_not_route`.

5) Atomic checkpoint
- checkpoint-объект должен писаться через атомарную запись (аналог `atomic_write_json`) в:
  - `runtime/agent-events/checkpoints/session-replay/{safe_session_id}.json`
- Протокол поля:
  - `schema_version`, `kind`, `processor_id`, `processor_version`, `provider`, `adapter`, `source_session_id`, `source_project_ref`, `last_raw_event_id`, `last_raw_location`, `updated_at`, `counts` (`seen`, `present`, `repaired`, `unsupported_mapping`, `denied`, `failed`)
- Правило прогресса:
  - checkpoint продвигается только после успешного завершения обработки текущей raw-записи.
  - при падении на конкретной записи checkpoint остаётся на последней успешно обработанной (см. `test_session_replay_checkpoint_advances_atomically_after_success`).

6) Денай по проекту/сессии (`cross-project denial`)
- Если `derived["project_root"]` (или source project mismatch в derived-сравнении) не соответствует `project_root` из native-envelope:
  - отказ с `not authorized` на Host-интеракции
  - no project repair execution for that raw record
  - raw записывается в журнал с сохранением приватности `privacy == "private"`
- Наблюдение из smoke:
  - `denied = ... expect=1`, и проверка ` "not authorized" in denied`
  - после этого `len(raw_records) == 4` и `all(record.get("privacy") == "private" for record in records)`.

## Факт-ориентированные наблюдения по raw-append/invariant
- Для одного успешного первого raw:
  - `accepted == True`
  - `deduplicated == False`
  - `len(raw_records(workplace))` растёт на 1
- Для повторной доставки того же raw с идентичным payload:
  - `deduplicated == True`
  - raw count **не** увеличивается.
- Для unknown hook:
  - adapter может возвращать `status == "delivered"`
  - `normalized_event_ids == []`
  - raw count увеличивается.
