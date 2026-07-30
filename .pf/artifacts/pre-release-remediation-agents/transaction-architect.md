# Отчёт transaction architect

- Дата: 2026-07-30
- Run: `pre-release-remediation-20260730`
- Assignment: `remediation-transaction-design-20260730`
- Роль: software architect, planning-only
- Product code изменён: нет
- Основной результат:
  `.pf/adr/pre-release-remediation-transaction-design-20260730.md`

## Результат

Разложены точные графы записи для `PF-AUD-010`, `PF-AUD-011`,
`PF-AUD-019` и process-create/dry-run части `PF-AUD-020`. Определён минимальный
общий transaction contract: pure preflight, per-filesystem staging,
write-ahead journal, entity-first/registry-last commit, reverse rollback,
post-commit audit/events/hooks.

Контрактных блокеров для реализации нет. Обнаружены две обязательные schema
dependencies и два смежных нарушения, которые нельзя потерять при реализации.

## Инструменты и ограничение

Анализ начат через Serena, как требует проектная политика.
`get_symbols_overview(tools/processforge.py)` вернул:

```text
Cannot extract symbols from file tools/processforge.py.
Active languages: []
```

После фиксации ограничения использованы только точечные поиски определений и
ограниченные line slices. Полное чтение монолитного файла не выполнялось.

## Exact symbols

### Общие writers/effects

- `resolve_platform_root`
- `write_resource_proposal`
- `write_resource_management_report`
- `append_workplace_resource_event`
- `append_process_event`
- `emit_process_event`
- `dispatch_hooks`
- `upsert_registry_entry`
- `write_yaml_file`
- `write_authoring_text`
- `append_authoring_log`

### Platform

- `normalize_platform_id`
- `command_platform_create`
- `platform_contract_path`
- `command_platform_contract_doctor`
- `command_platform_contract_install`

### Knowledge

- `resolve_package_root`
- `package_manifest_path_for_write`
- `load_workplace_package_manifest`
- `resource_index_path_for_package`
- `build_resource_index`
- `normalize_resource_record`
- `ensure_private_resource_path`
- `write_package_manifest_and_index`
- `command_knowledge_add_url`
- `command_knowledge_add_resource`

### Process

- `require_flow_root`
- `process_authoring_paths`
- `command_process_authoring_start`
- `write_process_authoring_example`
- `command_process_authoring_apply`
- `command_process_create`
- `event_runtime_paths`
- `dispatch_hooks`

## Подтверждённые write graphs и failure points

### PF-AUD-010

`command_platform_create` до doctor создаёт root/возможный root registry,
proposal, started event, двенадцать platform files и активную запись
`registries/platforms.yaml`. Затем doctor запускается против уже опубликованной
сущности, а `platform.authoring.completed` публикуется безусловно.

Точки отказа: mutating resolver, collision после audit writes, любой из
двенадцати последовательных file writes, registry validation/replace, doctor,
event append.

### PF-AUD-011

`write_package_manifest_and_index` пишет manifest раньше index. Ошибка
`index_path.parent.mkdir` или index write оставляет manifest изменённым.

Дополнительно `knowledge-add-resource` при private absolute path вызывает
`ensure_private_resource_path` из `normalize_resource_record` и меняет
`registries/private-resource-paths.yaml` до proposal и package update. Это
третья authoritative write, отсутствовавшая в формулировке finding.

### PF-AUD-019

`command_platform_create` использует canonical:

```text
<platform-root>/platform.<id>/platform-contract.yaml
```

`command_platform_contract_install` использует legacy:

```text
<workplace>/platforms/<id>/platform.yaml
```

Оба меняют одну запись `registries/platforms.yaml`; install может молча
перенаправить её и orphan canonical tree.

### PF-AUD-020, process-create

`command_process_create` пишет четыре session files и три process events до
того, как `command_process_authoring_apply` вызывает `require_flow_root`.
Финальная операция включает шестнадцать файлов. Шесть events могут породить
conditional hook outbox/result files. Текущий dry-run перечисляет только четыре
session files.

## Неочевидные дополнительные результаты

1. `private-resource-paths.yaml` и `platform-contract-roots.yaml` не имеют
   shipped JSON Schema и не включены в schema routing `upsert_registry_entry`.
   Для полного registry preflight нужны две новые схемы.
2. Рассмотренные command entrypoints ветвятся в основном по `args.dry_run`.
   Вызов без `--dry-run` и без `--apply` может дойти до записи. Transaction
   preflight должен требовать явный взаимоисключающий mode.
3. Proposal/event являются реальными mutations и потому не могут предшествовать
   pure preflight.
4. Process event dispatch имеет fan-out в hook outbox/results. После commit
   уже отправленные эффекты нельзя честно откатить; нужен idempotent audit replay,
   а не rollback authoritative state.

## Принятое архитектурное решение

Будущий implementation agent должен:

1. строить полный `AuthoringPlan` в памяти;
2. выполнять pure preflight без `mkdir`, proposal, event или hook;
3. stage-ить content на каждом целевом filesystem;
4. валидировать staged virtual view теми же pure checks, что используют doctors;
5. публиковать entity files;
6. публиковать registry documents последними;
7. при pre-commit ошибке восстанавливать точные pre-image hashes;
8. только после commit писать proposal/report/events и запускать hooks;
9. при post-commit audit failure оставлять valid committed state и
   `committed_audit_pending`, не обещая rollback уже dispatched hooks.

## Platform migration

Новые записи разрешены только в canonical layout. Legacy layout остаётся
readable с `WARN`. Обычные create/install не выбирают между двумя same-id
копиями.

Явная migration:

- переносит legacy-only contract в canonical path;
- при identical dual copy перепривязывает registry и архивирует legacy;
- при divergent dual copy блокируется до explicit source choice;
- фиксирует source/target hashes и prior/final registry entry;
- восстанавливает legacy path и registry bytes при отказе.

## Test matrix

В ADR задана injection matrix для:

- каждого stage и entity publish;
- каждого registry publish;
- invalid parent type;
- corrupt registry;
- missing dependency/failed doctor;
- duplicate/same-version collision;
- uninitialized process root;
- dry-run/apply parity;
- canonical/legacy conflict и migration rollback;
- event и hook failure после commit.

Негативный критерий: entity roots, registry bytes, ordinary event stream и hook
trees совпадают с baseline; допустим только отдельный failure journal.

## Future sole-writer scope

Рекомендованный изолированный scope:

```text
tools/processforge.py
schemas/private-resource-paths-registry.schema.json
schemas/platform-contract-roots-registry.schema.json
tools/validate-process-forge-schemas.py
tools/smoke_remediation_transactional_authoring.py
tools/smoke_remediation_platform_layout_migration.py
tools/smoke_remediation_process_create_transaction.py
.pf/artifacts/pre-release-remediation-agents/transactional-authoring.md
```

Начинать реализацию следует только после освобождения текущей sole-writer lease
на `tools/processforge.py`.

## Остаточные риски

- Между разными filesystems невозможен один физический atomic rename; гарантия
  строится на journal, backups и обязательном recovery.
- Directory replacement на Windows требует отдельного tested swap path, а не
  предположения о POSIX rename semantics.
- Audit/hook replay должен иметь stable transaction id/idempotency key.
- До добавления двух registry schemas нельзя заявлять полное соответствие
  schema-first transaction preflight.

## Статус

Architecture assignment выполнен. Product code и tests не изменялись. ADR
готов к независимому review и выдаче sole-writer implementation assignment.
