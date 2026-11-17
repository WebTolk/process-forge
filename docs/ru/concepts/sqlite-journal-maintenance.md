# Резервирование SQLite и обслуживание журналов

`journal-maintenance` — явная локальная операторская команда над общими службами
Core. Она создаёт проверяемые копии отдельных SQLite-баз, восстанавливает их в
новый файл, проверяет старые журналы событий/raw и импортирует их. Примеры ниже
запускаются из исходников; для установленной PF используется соответствующая
точка входа. Все пути в примерах — заполнители.

| Операция | Обязательные параметры | Сохраняемые изменения |
| --- | --- | --- |
| `backup` | `--database PATH --output BUNDLE` | Сразу создаёт новый проверенный комплект копии. |
| `verify` | `--backup BUNDLE` | Проверяет существующий комплект. |
| `restore` | `--backup BUNDLE --destination NEW_PATH` | Сразу создаёт новую базу. |
| `inspect` | `--project-root ROOT --workplace ROOT` | Проверяет журналы; явный `--evidence-dir DIR` записывает карантин. |
| `import` | `--project-root ROOT --workplace ROOT` | По умолчанию строит план. `--apply` разрешает импорт и запись копий/доказательств. Явный `--evidence-dir DIR` может записать карантин при планировании. |

Все операции принимают `--json` и всегда выводят ровно один JSON-объект в stdout,
включая обработанные ошибки выполнения. Код `0` означает успех или допустимый
план; `1` — отказ, повреждение/подмену, неудачу проверки либо ошибку ввода-вывода.
Ошибки синтаксиса аргументов сохраняют стандартный код argparse `2` и справку в
stderr; справка завершается кодом `0`. Операторские отчёты содержат частные пути
источников и доказательств. Храните их в закрытом месте; для публикации готовьте
обезличенную копию. Коды ошибок не включают содержимое записей и текст исключений.

## Копия, проверка и восстановление

Выберите новый каталог комплекта, родитель которого уже существует:

```sh
python -B tools/processforge.py journal-maintenance backup --database "DATABASE_PATH" --output "NEW_BACKUP_BUNDLE" --json
python -B tools/processforge.py journal-maintenance verify --backup "NEW_BACKUP_BUNDLE" --json
python -B tools/processforge.py journal-maintenance restore --backup "NEW_BACKUP_BUNDLE" --destination "NEW_DATABASE_PATH" --json
```

`backup` и `restore` записывают файлы сразу, без параметра `--apply`. Существующий
каталог комплекта или файл назначения отклоняется. Родитель назначения должен
существовать. Backend отклоняет небезопасные символические ссылки/reparse-пути
и неожиданные элементы комплекта.

Комплект состоит из `database.sqlite3` и `manifest.json`. Источник открывается
только для чтения, копирование использует SQLite backup API и учитывает
зафиксированные данные WAL. Проверяются структура манифеста, состав комплекта,
стабильные SHA256 и `PRAGMA integrity_check`. Восстановление проверяет комплект
до создания нового назначения, проверяет результат и сохраняет исходную копию.
Храните манифест рядом с базой: хеши выявляют изменения относительно манифеста,
но не заменяют независимую подпись или подтверждение происхождения.

Одна копия представляет снимок одной базы. Снимки нескольких баз имеют отдельные
границы согласованности. Восстановление создаёт отдельный файл; переключение
установки на него выполняется существующими операторскими процедурами.

## Проверка перед импортом

Укажите существующий проект с `.pf/process-forge.yaml` и явный корень workplace.
Поиск читает старый `runtime/events/events.ndjson` под PF flow root проекта,
общие raw-shard файлы под `runtime/agent-events/raw/v1/` workplace и поддерживаемое
старое расположение raw внутри проекта. Для импорта отбираются raw-записи только
выбранного проекта.

```sh
python -B tools/processforge.py journal-maintenance inspect --project-root "PROJECT_ROOT" --workplace "WORKPLACE_ROOT" --json
python -B tools/processforge.py journal-maintenance inspect --project-root "PROJECT_ROOT" --workplace "WORKPLACE_ROOT" --evidence-dir "NEW_QUARANTINE_DIR" --json
python -B tools/processforge.py journal-maintenance import --project-root "PROJECT_ROOT" --workplace "WORKPLACE_ROOT" --json
```

Проверка и план импорта не изменяют базы назначения. Без явно указанного каталога
доказательств они не создают сохраняемые доказательства в проекте. Явный каталог
разрешает запись карантина, в том числе при отказе из-за повреждения. У `inspect`
нет параметра пропуска. Повреждённые строки дают `status: blocked` и код `1`.
Одинаковая identity с разным содержимым остаётся ошибкой даже при разрешённом
пропуске повреждённых строк.

Карантин сохраняет точные байты каждой повреждённой строки, включая NUL и окончания
строк. `manifest.json` содержит источник, номер строки, байтовое смещение, длину,
SHA256, причину и ссылку на файл `records/*.bin`. Отчёт указывает путь и хеш
манифеста. Существующие совпадающие доказательства используются только после
проверки; конфликтующие отклоняются. Сохраняйте манифест, бинарные файлы,
неизменённые исходные журналы и операторский отчёт вместе.

Если проверка прервана после обнаружения повреждения, файл
`manifest.incomplete-*.json` сохраняет уже захваченные байты и provenance с
`scan_complete: false` и кодом причины. Он не подтверждает полную проверку
источника. Готовый манифест предыдущего прохода сохраняется. Доказательства отказа
импорта явно отмечают незавершённый preflight; их счётчики не подтверждают полный
проход. Конфликты ID и дрейф источников по-прежнему требуют исследования.

## Явный импорт и повторный запуск

До применения согласуйте переключение старых писателей журналов через обычные
операторские процедуры. Проверьте план, сохраните оригиналы и доказательства.

```sh
python -B tools/processforge.py journal-maintenance import --project-root "PROJECT_ROOT" --workplace "WORKPLACE_ROOT" --apply --evidence-dir "MAINTENANCE_EVIDENCE_BASE" --json
```

Применение создаёт уникальный каталог операции внутри явной базы доказательств
либо в `.pf/runtime/journal-maintenance/` проекта по умолчанию. Повреждённые байты
сохраняются даже при отказе импорта. До изменения существующих баз назначения
создаются проверенные копии; отсутствие базы фиксируется отдельно. Назначения:
`runtime/events/events.sqlite3` и `runtime/agent-events/hooks.sqlite3` под flow root
проекта.

Пропуск повреждений требует явного выбора оператора после изучения отчёта:

```sh
python -B tools/processforge.py journal-maintenance import --project-root "PROJECT_ROOT" --workplace "WORKPLACE_ROOT" --apply --skip-invalid --evidence-dir "MAINTENANCE_EVIDENCE_BASE" --json
```

`--skip-invalid` применим и к плану, но не включает `--apply`. Корректные ID и
исходные envelope сохраняются. Успешный импорт проверяет стабильность источников,
целостность SQLite, уникальные ID/числа записей, состояние миграции и семантический
повтор. Повторный явный импорт использует существующую дедупликацию; уже имеющиеся
записи учитываются без повторной вставки. Каждая попытка применения сохраняет
собственные доказательства и резервные копии.

Поле `counts` отчёта импорта разделяет `read`, `valid`, `imported`,
`already_present`, `skipped`, `corrupted`. Проверка также показывает `read_rows`,
`valid_rows`, `invalid_rows`, `skipped_rows`, `duplicate_rows`, пустые/отфильтрованные
строки и суммы по видам журналов. Корректные строки включают дубли. Пропуски импорта
включают raw другого проекта и повреждённые строки только при явном skip;
проверка учитывает фильтрацию отдельно. Повреждения остаются повреждениями в
доказательствах.

Прерванный импорт сохраняет барьеры незавершённой миграции и доказательства для
восстановления. Перед явным повтором изучите состояние назначений по сохранённым
отчётам фаз/ошибок. Отказ обязательной копии, доказательства или проверки остаётся
ошибкой. Изменение источника и конфликт identity требуют операторского разбора;
force-параметра и автоматического переписывания источников нет.

## Границы обслуживания

Обслуживание сохраняет исходные журналы и исторические PF-артефакты. Команды не
исправляют контексты, не создают/возобновляют исторические Work, не меняют grants,
не обновляют установку и не запускают/останавливают Runtime, MCP и другие службы.
Проверки источников и хешей обнаруживают наблюдаемые изменения; переключение
писателей контролируется операторскими процедурами. Нового MCP endpoint или
shell passthrough нет.

`tools/migrate-hook-journals.py` сохраняет явный интерфейс plan/apply/skip как
тонкий адаптер той же службы; дополнительный `--evidence-dir` выбирает хранение
доказательств. Контекст владения журналами и переключения описан в
[Журналы проекта в SQLite](hook-journal-sqlite.md).

## Engine execution storage: исходная фаза R02

`ExecutionMigrationService` переносит только наблюдаемые latest `status.json` в
main store проекта. Сохраняются явные project/run/task/attempt IDs, неизвестные
поля compatibility DTO и точные исходные bytes. Имена числовых attempt-каталогов
задают allocation floor; их тела не читаются для выдуманного восстановления
истории. При независимо доказанном quiescence directory-only факты сохраняются в
`execution_allocation_floors` без execution/head/current/history rows. Например,
`attempts/7` без status импортирует ноль executions и резервирует 8 для первой
реальной allocation. Отсутствие status не доказывает idle. Manifest закрепляет
каждое валидное имя каталога: добавление, удаление или переименование даже меньшего
номера меняет plan. Пропущенные доказанно исторические snapshots также сохраняют
floor. Полнота истории не заявляется. Unknown/current activity,
неоднозначные имена, drift/foreign schema и отсутствие явного `project.id`
блокируют перенос.

К замороженным Database/repository/admission/BackupPort добавлен приватный typed
`safety` verifier. `ExecutionMigrationContext` закрепляет authorized project и
workplace routing, project/store/target, поколения, plan и checksum всего inventory.
Host доказывает исключение старых writers, отсутствие pre-spawn gap и всех owned
process trees, сверяет Runtime instance/routing/capabilities. Freeze, resume и
проверка перед cutover происходят под admission. Missing/stale/exception/active/
unknown proof дают отказ; `offline_confirmed` означает только намерение оператора.
Техническое fencing произвольных старых binaries не заявляется.

Inspect/plan не создают БД или binding. Явный evidence ограничен `maintenance/`
actual flow root. Manifest потоковый, порядок relative paths — raw UTF-8;
буфер содержит до 256 имён каталогов или записей import. При большом fanout
read-only сортировка повторяет проходы каталога. Тела ограничены 64 KiB;
stdout/stderr, report и prepared-input не читаются. Skip допускает только
положительно исторический invalid snapshot при полном host proof; точные bytes,
checksum и provenance остаются в evidence.

Apply под admission публикует pending `data/execution-storage.json` до mutation.
Для существующей БД создаётся одна проверенная WAL-aware recovery backup. Batch
содержит до 256 source units: snapshot вместе с floor либо отдельный floor-only
факт. Import и checkpoint коммитятся в одной транзакции даже при пустом наборе
ExecutionRecords. Checkpoint считает все units (`counts.import_units`),
`counts.imported` — snapshots, `counts.floor_only` — отдельные floors. Перед cutover
проверяются schema/source/count/FK, точное floor parity до replay и no-op replay
snapshots. Отдельный deterministic `verification/` bundle через
BackupPort проверяет SQLite integrity, сохраняя запрет административных PRAGMA в
публичном SqlSession. Resume сверяет и переиспользует оба bundle; verification
не заменяет исходную recovery backup. Единственная CAS-транзакция одновременно
делает `execution_state` SQL-ready и переводит migration marker в ready.

Resume выбирается точными migration_id/plan_checksum/evidence. Pending binding
блокирует capable execution clients без fallback к JSON. После cutover resume
чинит только derived report; dirty heads остаются владельцу indexed projection.
Изменённый позднее status.json не импортируется как truth. Явный `abort` удаляет
только собственный pending binding до любых target/schema mutations. После
schema/import commits нужен roll-forward; restore требует нового target и
контролируемого offline переключения binding.

Command/parser добавляют execution-inspect, execution-import (по умолчанию plan),
execution-resume. Для apply нужны --apply --offline-confirmed и --evidence-dir;
resume также требует точных migration/checksum selectors. Вывод — один JSON,
exit 0 для plan/ready, 1 для отказа и argparse 2 для неверного синтаксиса.
Без host composition/verifier новые операции fail-closed.

## Явная миграция и UUID

`StorageMigrationService` выполняет явную операцию оператора/updater.
`tools/migrate-storage.py` принимает `--project-root` и/или `--workplace-root`,
необязательный `--device-config` и один из `--inspect` (по умолчанию),
`--apply`, `--resume`. Apply/resume требуют `--offline-confirmed`: в Гараже
оператор остановил PF и писателей, в Кузне updater управляет единственным
исполнителем PF. Коды выхода: 0 planned/ready, 1 blocked/failed, argparse 2.

Сначала импортируйте event/raw командой выше, затем выполните:

```text
python -B tools/migrate-storage.py --project-root PROJECT --workplace-root WORKPLACE --apply --offline-confirmed --json
```

Обычные записи Work/worker проверяют готовность и отклоняют legacy storage с
`storage_migration_required`; автоматического импорта при первой записи нет.
Pure reads не создают migration files. Явные stop/cancel/collection существующей
попытки сохраняются для recovery и не разрешают запуск новой попытки.

Для распознанных events/raw/accounting/search добавляются только pf_store_meta,
pf_schema_versions и store_identity@1. Пути, domain application IDs/versions,
DDL/constraints/indexes/FTS shadow objects, строки/ID/blob не меняются.
Exact fingerprints закреплены в storage-migration-v1.json; unknown extra,
foreign/future/corrupt/drift отказывают. Search baseline: meta.schema_version=6,
application_id/user_version=0/0. Это квалификация конкретных схем, не всех старых
релизов. Project owner берётся из explicit manifest project.id; accounting — из
existing origin_id в data/accounting/identity.json. Другие workplace targets
требуют квалифицированного стабильного host owner source; новое ID не mint.
Main сохраняет строгий W2 envelope и только execution-storage binding.

Owner-local data/storage-identities.json закрепляет relative target/UUID/owner,
pending/ready и plan checksum. Exact selector в
data/storage-migrations/r02-storage-v1/targets/ сохраняет planned UUID до pending;
immutable plan и journal находятся в checksum directory. UUID не remint, first/
newest journal не выбирается. До metadata transaction нужен проверенный WAL-aware
backup, связанный с source schema/logical fingerprint и планом. Streaming typed
row digests/counts, integrity/FK проверяют parity без новых metadata.
Resume проверяет тот же backup/source и восстанавливает сбой между metadata commit
и ready pin. Per-target commits и file journal не являются общей транзакцией;
предыдущие ready targets не откатываются при сбое следующего.

storage_identity_access удерживает owner identity gate до закрытия connection;
ready проверяет UUID/owner/schema, pending отказывает, metadata без pin не remint.
Internal backup использует raw injected driver без recursive migration.
new_store_identity публикует pending до explicit writable domain initialization;
add_store_identity добавляет metadata в его транзакции. При сбое повторный explicit
initializer использует тот же UUID. Unused absent stores не создаются. Rebuild
сохраняет UUID либо требует controlled rebind; backup/restore UUID сохраняют.

Execution import, source originals, batches<=256/checkpoint и единственный SQL CAS
остаются у исходного ExecutionMigrationService. Coordinator вызывает его через
exact durable selector; история не выдумывается, main не получает второй pin.
После cutover SQL остаётся authority; projection repair выполняет его владелец.

Host закрепляет один configuration snapshot, точные roots, стабильных owners и
выбранные targets. Явное обслуживание требует реального admission и отклоняет
известный работающий Runtime. Перед изменением повторно проверяется тот же выбор.
Это локальное обслуживание под ответственностью оператора/updater; техническое
исключение любого неизвестного исторического процесса не заявляется.

Для продолжения используйте те же roots и `--resume --offline-confirmed`.
Pending identity, изменения source/schema/transform, чужие UUID, неизвестные
активные executions и повреждённое recovery evidence сохраняют отказ. Изменение
кода не переписывает старый pending plan и не отменяет его проверки.
См. [execution storage](execution-storage.md#явная-миграция-и-ответственность-за-обновление).
