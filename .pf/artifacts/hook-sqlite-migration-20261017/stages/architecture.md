# Architecture, implementation plan и decision log

Дата: 2026-10-17. Объём принят из domain.md и явного поручения пользователя. Это source-архитектура, установленный Runtime не переключается автоматически.

## Владельцы хранения

1. `src/processforge_core/sqlite_storage.py`: закрываемые operation-local connections, SQLite transactions/schema checks, WAL, busy timeout, FULL synchronous и migration-ready marker. Чтение отсутствующей БД не создаёт файл; чужая/неполная схема не принимается молча. Минимальная версия SQL использует ON CONFLICT, без зависимости от RETURNING.
2. `ProcessEventJournal`: `.pf/runtime/events/events.sqlite3`. Tables:
   - `admissions`: seq, уникальный event_id и минимальный digest. Устойчивая дедупликация независимо от history flag.
   - `events`: сохранённый envelope и indexed поля event type, assignment, subject, session, run, time; seq из admission. Только при включённой истории.
   - `verification_state`: последнее verification envelope/fingerprint по assignment/event type; это ограниченное рабочее состояние, обновляется независимо от history flag.
   - metadata: количество сохранённых событий и migration state. Count/latest/ID/latest-assignment читаются индексированно; pagination по seq.
3. Raw SQL owner и `RawIngressKernel`: `.pf/runtime/agent-events/hooks.sqlite3`. Tables для уникальных raw/native identities, optional raw record, pending native record, итогового receipt/status и quarantine. Runtime kernel сохраняет существующие identity/provenance helpers. История raw и обязательные данные pending различаются: без raw logging завершённый payload удаляется, ID/digest остаются.

До derived effects raw receipt фиксируется отдельно; общей транзакции с внешним chat/Ledger/YAML не обещается. Повторы безопасны за счёт прежних детерминированных sink IDs и indexed admissions; завершённый ingress может вернуть сохранённый итог. Незавершённые/отложенные записи остаются пригодными для replay. Ошибка до commit не даёт успешного подтверждения.

Ни поиск ID, ни обычный append не читают NDJSON/всю SQL history. Полное чтение допускается только для explicit export/rebuild/doctor/migration. Старый registry lock вокруг event append заменяется SQL transaction, без удаления старых live lock-файлов.

## Config API

- Сохраняется immutable PFConfig и действующий global metrics field. Добавляется `LoggingConfig(raw_hooks=True, events=True)`.
- `ProjectPFConfig` содержит только nullable logging overrides; отдельная strict schema. Global configuration не принимает null для bool; проектный null означает inherit.
- Существующие ConfigService/YamlConfigStore получают явный default/model для проекта; прежние signatures/default behavior global CRUD сохраняются.
- `PFConfig` объединяет global и overrides в effective immutable snapshot. Путь global прежний `<workplace>/configuration.yaml`; project `.pf/configuration.yaml`.
- Ограниченный thread-safe per-process resolver кеширует snapshots по filesystem identity/mtime/size и перечитывает при create/replace/delete. Не читает YAML для каждого хука. Ошибка после валидной загрузки сохраняет последний валидный snapshot и доступную диагностику; первая некорректная конфигурация не принимается молча.
- CLI `config ... --workplace ... --project-root ...` управляет project overrides; read показывает overrides/effective values. Delete одного project key возвращает inherit, delete файла возвращает полное наследование. Только два logging поля разрешены в project scope.

## Интеграция

- Core event path меняется на SQLite. Append получает effective logging flag, но всегда обновляет минимальный admission и при наличии verification fingerprint — рабочее последнее verification state. Project hooks dispatch выполняется для новой admission, независимо от history flag.
- Core readers, cancellation replay, worker-completion lookup и automation readiness используют SQL owner. Generic NDJSON reader остаётся для реально NDJSON подсистем; binary SQL не передаётся текстовому reader.
- Host использует project raw root, effective raw flag и SQL lookup. Убираются безусловные rebuild_projection/rebuild_stage_obligations из `_ingest_derived_event`.
- History Markdown — explicit rebuild/export. Periodic stage projection использует сигнатуру входных файлов и обновляется при изменении; gate/readiness продолжает проверять актуальные authoritative inputs, без доверия одному UI cache.
- Runtime observer latest/count читает SQL, без чтения всего файла. Provider registry и Codex entry сохраняются. Existing chat capture/transport остаётся работоспособным; полное обновление chat storage/UI не входит в этот срез.
- Raw replay читает SQL rows по session/provider/project; checkpoint/provenance checks сохраняются.

## Временный мигратор

`tools/migrate-hook-journals.py`, явные `--project-root`, `--workplace`, `--apply`; без apply — анализ/план. Stream read старого project events.ndjson и workplace raw hourly shards, raw фильтруется по проверенному project ref. Переносит старые event/raw IDs, envelope, order, native identity и связь с исходным location. Конфликты и invalid rows отражаются в отчёте; пропуск повреждений требует отдельного явного флага. Миграция не меняет/удаляет исходные файлы.

Import markers не дают normal readers/writers использовать частично перенесённую БД. Повторный запуск использует unique IDs и безопасно доводит импорт. После полного импорта проверяются source stability, counts и SQLite integrity; только затем marker ready. Непустой legacy journal без завершённого импорта требует migrator, а не молчаливого создания новой истории.

Мигратор не останавливает процессы и не обновляет installed Core. Для реального переключения должны прекратиться записи старого Core; source acceptance использует fixtures/снимки. Удаление мигратора — отдельная будущая задача после переключения всех нужных проектов.

## Порядок реализации и проверки

1. SQL helper/event owner и indexed readers; isolation, ID uniqueness, rollback/reopen, optional history/verification state.
2. PFConfig models/store/resolver, schema/template/CLI, inheritance CRUD и live reload.
3. Raw SQL owner/kernel/Host/replay, завершение pending и сохранение конфликтных diagnostics.
4. Все Core/Runtime readers, projections и doctors; существующие consumers не должны читать frozen NDJSON.
5. Малый migrator, docs и необходимые существующие smoke updates.
6. Изолированный focused suite: шесть конкурентных producers и retries, transaction failure/reopen, raw off + pending/recovery, history off + Work/check/chat, все overrides/config changes, non-destructive rerunnable migration, invalid/conflict paths, отсутствие full-read/rebuild на ingress. Query plans подтверждают использование индексов; timings — измерения этой среды, не универсальные обещания.
7. Собственный коммит и dual push/readback в рамках delivery; source и device acceptance различать.

## Решения и ограничения

- SQLite выбран по прямому поручению; новый сервис БД/зависимость не нужен. Схема остаётся локальной проектной private runtime persistence; canonical Work YAML не переносится.
- Два файла БД дают отдельного владельца raw receipt и normalized facts, как и прежняя raw-first архитектура; между ними действует recoverable processing, не ложная atomicity.
- Два bool settings не превращаются в новую систему уровней UI. Семантическая/техническая фильтрация истории может использовать event types при последующем UI развитии.
- Не сохранять скрытую полную историю при выключении флага: receipts содержат минимум, verification_state — только последнее рабочее состояние, completed raw pending очищается.
- Не считать raw payload log надёжной очередью сам по себе. Незавершённая обработка сохраняет необходимый native input, даже когда долговременная raw-копия выключена.
- Не расширять эту задачу до общего асинхронного worker engine или новых agent adapters; текущие тяжёлые full scans устраняются в существующем ingress.
