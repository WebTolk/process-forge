# Investigation и impact analysis

Дата: 2026-10-17. Источники проверены через Serena и точечное чтение. Product edits ещё не начаты.

## Фактический путь

- `tools/pf_runtime/host.py::_ingest_event` разрешает проект, создаёт NativeAgentEvent, сохраняет raw receipt, проверяет доверенный адаптер, затем применяет derived event и conversation capture.
- `_ingest_derived_event` под общим state lock нормализует один input, проверяет ID, пишет canonical event, затем безусловно перестраивает command history и все stage obligations. Повтор тоже вызывает обе перестройки.
- `ProcessEventJournal.contains/append` читает весь NDJSON; кеш ID проверяется хешем всех байтов. Оптимизация должна заменить владельца хранения, а не только один caller.
- RawIngressKernel пишет hourly shards, file indexes, recovery checkpoint и quarantine. Host использует workplace root; replay читает те же shards. Здесь нужна проектная изоляция и SQL-индексы.
- `codex_hooks.dispatch` повторяет тот же envelope через fallback после неуспеха Runtime. ID и подтверждение после commit должны переживать этот повтор.

## Читатели, которые требуется перевести

1. Core append/paths, worker-completion duplicate lookup, run-doctor optional event check, events/chat schema doctor и snapshot events path в `tools/processforge.py` и `src/.../project/snapshot_rendering.py`.
2. Runtime history rebuild, journal lookup, verification-event lookup, event count и service last-event observer.
3. `AutomationReadinessService.latest_assignment_event`: читает весь journal и выбирает последний verification event. Это реальная функциональная зависимость, не только отображение.
4. Cancellation replay читает journal через переданный callback; completion replay уже восстанавливает authoritative YAML из отдельного intent и генерирует детерминированные event IDs.
5. Raw replay/session recovery и их checkpoint/provenance checks.
6. Связанные smoke/fixtures: process-event concurrency, central ingress/replay, raw recovery, lifecycle identity, conversation completeness, first-run, diagnostics, runtime host/status/metrics, Work recovery, configuration CRUD/schema, process execution support и schema validator.

Work/run/assignment state и evidence хранятся в YAML/artifacts. Task doctor публикует `task.doctor.passed/failed` с `verification_fingerprint`; readiness потом ищет этот факт в journal. Его последнее состояние следует хранить независимо от выключаемой истории. Cancellation/completion/worker повтор должен опираться на минимальные ID receipts, а не наличие исторической строки.

Chat имеет отдельные private transcripts с содержимым и metadata-only `chat.message.recorded` в event stream. Chat transport/доставка должны продолжать работать при выключенной записи истории. Миграция этих двух журналов не объявляет полноту захвата переписки: она зависит от фактически зарегистрированных hooks и доступных полей провайдера.

## Конфигурация

`PFConfig` — frozen dataclass, schema 1; пока только runtime metrics interval. `ConfigService` предоставляет revision-checked CRUD. `YamlConfigStore` проверяет strict YAML, размер, путь, использует native locking и atomic replace. Глобальный файл — `<workplace>/configuration.yaml`; Runtime уже перечитывает его и сохраняет последний валидный snapshot. CLI ownership — `tools/pf_cli/commands/configuration.py` и `parsers/configuration.py`, поэтому добавлены в successor scope.

Проектные overrides должны храниться в `.pf/configuration.yaml`, иметь два nullable поля и отдельную strict schema; null/отсутствие наследует глобальное. Нельзя читать YAML на каждом lookup: нужен ограниченный per-process cache по файловой ревизии/metadata, инвалидируемый replace/create/delete.

## Контракты и знания

Прочитаны `.pf/AGENTS.md`, manifest и capsule, accepted ADR config-driven-behavior и file-flow-canonical-contract, `process-events.md`, `hooks-events.md`, `runtime-model.md`, `provider-adapters.md`; root Python и Python practices разрешены текущим Work. Локально прочитаны PEP 8, frozen dataclasses, with/context-manager contract. Проект не фиксирует Python toolchain overlay; доступные shared toolchains — PHP/JavaScript, их gates к Python не применяются.

Официальные исследования: SQLite WAL/query planner/UPSERT/appropriate uses, Python sqlite3 transaction/thread/connection contract; ссылки в `.pf/logs/hook-ingress-framework-research-20261017.md`. Текущая среда: Python 3.14.3, SQLite 3.50.4, sqlite3 threadsafety 3. Новые зависимости не нужны. Использовать явные transactions и закрытие соединения; connection context manager сам по себе не закрывает connection. Общая connection между потоками не требуется.

## Impact и ограничения

SQLite заменяет private runtime journals; YAML manifests/Work/capsules остаются canonical. Формат и путь private journal меняются по прямому поручению пользователя, envelopes/IDs/adapter admission сохраняются. Public CLI/MCP semantic fields сохраняются; project config CLI расширяется явно.

`tools/pf_runtime/service.py` имел preexisting Git M без содержательного diff; не включать чужие изменения. После стартового overlap Work пересоздан с exact predecessor handoff, чужой smoke исключён. Source, installed, Runtime и connected-host qualification различать.

Мигратор нужен до первого нового writer, если старый непустой journal существует; не допускать молчаливого начала пустой SQLite-истории. Сохранять исходники; повреждения/ID conflicts показывать явно. Live device переключается отдельно, после остановки старых writers оператором/отдельной разрешённой процедурой.

Готово к domain modeling: источники истины и опасные зависимости установлены; осталось зафиксировать SQL schema, off-semantics, восстановление и migrator protocol.
