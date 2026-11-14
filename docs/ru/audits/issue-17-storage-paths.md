# Поддерживаемые storage-пути и квалификация восстановления

Инвентаризация фиксирует реализованные входы для №17. Каждый путь требует
указанных доказательств владения и безопасности. Тест с injected host proof
или UUID metadata не квалифицирует границу старых писателей в установке.
Обслуживание PF Core и lifecycle пакетов имеют разных владельцев:
обновление пакета не запрашивает обслуживание всего рабочего места.

Flow root проекта выбирается явно. Main profile по умолчанию — `project_main`
с путём `data/pf.sqlite3`; разрешённый alias обязан совпадать с существующим
execution binding. Identity проекта берётся из явного manifest `project.id`,
а не имени каталога.

| ID | Вход и реализованный переход | Authority и восстановление |
| --- | --- | --- |
| ST01 | `select_execution_storage`: подключение ready main по точным binding/profile. | Сохраняются project/store identity. Pending, отсутствующий, foreign или конфликтующий bound store дают отказ без JSON fallback. Чтение ничего не создаёт. |
| ST02 | `storage_identity_access`: подключение recognized ready events/raw/accounting/search store по owner slot. | Owner identity gate удерживается до закрытия adapter connection. Проверяются UUID, scope/owner, kind/path и доменная схема. Pending и unpinned adopted metadata запрещены. |
| ST03 | `migrate-storage.py --apply`, update/first-write coordinator: UUID adoption существующей recognized DB на месте. | Сохраняются доменные IDs, rows, blobs, объекты схемы и путь. Active/unknown до pending откладывают adoption без нового UUID и скана истории. Exact selector/plan/pending публикуются до mutation. |
| ST04 | `migrate-storage.py --resume`: восстановление точного adoption plan. | Используются прежние UUID, descriptor, source facts, backup и generation. Metadata commit с отставшим file journal восстанавливается вперёд. Targets коммитятся независимо; поздний отказ не откатывает ready target. |
| ST05 | `journal-maintenance execution-import`, coordinator main import: latest snapshots и allocation floors в main SQL. | Нужны qualified quiescence и exclusion старых писателей. Pending binding публикуется первым. Batch ≤256, import и checkpoint одной transaction. Единственный ready/sql CAS устанавливает authority. Утраченную историю не выдумывают. |
| ST06 | `execution-resume`, coordinator main recovery. | Exact migration/checksum/evidence selectors и прежние backup/checkpoint. До cutover перепроверяются frozen sources и safety. После ready SQL остаётся authority, JSON — только projection. |
| ST07 | `new_store_identity` плюс `add_store_identity`: явная инициализация нового writable domain target. | Pending предшествует созданию, metadata коммитится вместе с доменной инициализацией. После сбоя используется тот же UUID. Inventory не создаёт неиспользуемые absent stores. |
| ST08 | Явная успешная инициализация нового flow root: fresh main SQL publication. | Existing/forced init не считается fresh. Durable pending initializer закрывает legacy даже до binding. Repair использует точные owner/UUID/profile и qualified native capability. |
| ST09 | Offline-перенос целого проекта с неизменными относительными bindings. | Сохраняются project/store identity, accepted resources, relative paths и profile. Это не произвольный live rebind. Engine test проверяет rename с injected host dependencies; физический перенос требует отдельной deployment qualification. |
| ST10 | `journal-maintenance backup/verify/restore`: один SQLite snapshot в verified bundle и новый absent destination. | Учитывается committed WAL, сохраняются UUID/data и bundle. Existing/unsafe/tampered destination запрещён. Restore не переключает live binding. Снимки нескольких DB независимы. |
| ST11 | `journal-maintenance inspect/import`, legacy `migrate-hook-journals.py`: recognized events/raw journals в project journal DB. | Сохраняются IDs/envelopes, originals, quarantine и backups. Writer cutover принадлежит оператору. Drift/conflicting duplicate запрещены даже с skip-invalid; после сбоя остаётся incomplete barrier для явного retry. |
| ST12 | Managed PF Core update либо qualified first cold transition, затем maintenance свежим installed code. | Core publication и storage readiness принимаются отдельно. Сохраняются exact selection, epoch, store UUID/bindings и recovery owner. Linux cohort/baseline fence сами по себе не реализуют и не квалифицируют весь переход. |

## Recognized target layouts

Пути относительны выбранному flow root проекта либо workplace root.

| Scope / kind | Путь | Источник stable owner |
| --- | --- | --- |
| Project events | `runtime/events/events.sqlite3` | Явный project ID в manifest |
| Project raw | `runtime/agent-events/hooks.sqlite3` | Явный project ID в manifest |
| Standalone project search | `runtime/local-resource-search/search.sqlite` | Явный project ID; только без workplace |
| Project main | `data/pf.sqlite3` либо exact selected profile alias | Явный project ID; execution binding без второго legacy pin |
| Workplace raw | `runtime/agent-events/hooks.sqlite3` | Stable ID выбранного workplace manifest |
| Workplace search | `runtime/search/local-resource-search.sqlite` | Stable ID выбранного workplace manifest |
| Workplace accounting | `data/accounting/accounting.sqlite3` | Существующий origin ID из `data/accounting/identity.json` |

Отсутствующая workplace/accounting identity даёт per-target unqualified diagnostic.
Targets должны быть внутри выбранных owner roots и физически различны.
Изменение profile не переносит bound DB.

## Отсутствующие автоматические переходы

Не реализованы произвольный live rebind, restore поверх bound live DB,
old-Core rollback после SQL commits и adoption неизвестных remnants. Restore
создаёт новый destination; controlled offline binding switch выполняется отдельно.
Old-Core rollback требует отдельно qualified reverse export. Execution abort
ограничен границей до mutation; committed import/schema восстанавливается вперёд.
Новый workplace main, объединение всех legacy-доменов и другие drivers вне состава.

## Maintained evidence

Workflow `Storage recovery qualification` запускает migration, identity,
automatic-policy, admission, database, backup, journal и projection suites
на реальных Windows и Linux, сохраняет JUnit и запрещает пропуск применимых
сценариев. Windows device-name и NTFS junction assertions явно исключены в Linux.
В Linux проверяются настоящие symlinks; в Windows — reparse paths, включая
существующий junction integration test.

Engine fixtures используют deterministic injected safety. Они проверяют алгоритмы,
checkpoint atomicity, schema/UUID refusal, WAL/physical source drift и порядок
восстановления. Эти результаты не подтверждают deployment eligibility,
полноту покрытия писателей или весь Core-update/release transition. Для этого
нужны actual OS evidence выбранного native provider.

См. [Execution storage and authority](../concepts/execution-storage.md),
[SQLite maintenance](../concepts/sqlite-journal-maintenance.md) и
[English inventory](../../audits/issue-17-storage-paths.md).
