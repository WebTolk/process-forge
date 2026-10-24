**W2 — дизайн общего SQL API и SQLite-драйвера PF**

Дата: 2026-10-24. Статус: `ready_for_review`, только дизайн.

Run: `pf-r02-design-20261024`  
Assignment: `pf-r02-w2-driver-design-20261024`, attempt 2  
Context: `pf-r02-w2-driver-design-20261024-capsule`

**Проверенное состояние**

- `sqlite_storage.py::database/transaction` уже обеспечивают operation-local connections, явные транзакции, WAL/FULL и migration barriers. Это SQLite-helper, общего SQL API пока нет.
- `ProcessEventJournal`, `RawHookJournal` и `SQLiteAccountingRepository` используют разные `application_id`. Общие имена `journal_metadata` также препятствуют простому объединению схем.
- `AccountingService` непосредственно использует SQL, `sqlite3.Connection` и конкретный repository. Одной замены connection factory недостаточно для сменяемости backend.
- `PFConfig/ProjectPFConfig` строго проверяют поля; профилей БД нет. `ConfigService/ConfigStore/YamlConfigStore` уже отделяют настройку от хранения конфигурации.
- `BackupPort/SQLiteBackupService` и `JournalMaintenanceService` предоставляют существующие механизмы backup, проверки и управляемого импорта.
- `ResourceIndexBackend` относится к поиску; основной SQL-драйвер через него не строится.

**Предлагаемый минимальный API**

Публичный пакет — `processforge_core.database`, доступный Core и процессам обычным Python import, без CLI, Runtime bootstrap или глобального singleton.

| Контракт | Ответственность |
| --- | --- |
| `DatabaseDriver`, первый `SQLiteDriver` | Подключение, возможности backend, привязка параметров, перевод ошибок |
| `Database.read()` | Одна read-only сессия с согласованным snapshot |
| `Database.transaction()` | Одна явная атомарная write-сессия |
| `SqlSession` | `fetch_one`, ограниченный `stream`, `execute`, пакетный `execute_many` |
| `SchemaManager` | Раздельные `inspect`, явные `initialize/apply` |
| `DatabaseFactory.from_profile()` | Проверка профиля и уже разрешённого target без I/O |

`SqlValue`: `None | int | float | str | bytes`; int ограничен signed-64, float конечный. Boolean, даты, Decimal, UUID и JSON преобразуются явно доменными codecs. `SqlRow` возвращает неизменяемые значения и имена колонок; SQLite cursor/connection наружу не выходят.

Первый `SqlStatement` использует `dialect="sqlite"`, `?` и связанные параметры. Произвольный SQL не объявляется переносимым. Будущие backend заменяют repository SQL adapter; доменные use cases сохраняют Protocol/DTO. Это позволяет обойтись без ORM, полного builder и собственного универсального SQL-парсера.

Конструкторы ничего не открывают и не создают. Обычные режимы `ro/rw` не создают отсутствующую БД. Чтение использует `BEGIN`; запись — `BEGIN IMMEDIATE`, commit после успешного тела, rollback при исключении. Вложенные транзакции и скрытые повторы запрещены. Cursor закрывается при досрочном прекращении потока.

Для managed PF stores обязательны проверяемые WAL/FULL, FK и ограниченный busy timeout. Настройка WAL и DDL выполняется административной операцией. Длительные backup, export и миграционные циклы не удерживают оперативную write-транзакцию.

Ошибки API содержат стабильный код без SQL, параметров, DSN и исходного текста исключения. Доменные адаптеры сохраняют существующие публичные ошибки, payloads и exit codes. Отсутствующая или недоступная БД текущих исполнений не означает «активности нет».

**PFConfig и расположение**

Предлагается необязательная секция `database` с именованными profiles и defaults `workplace_main/project_main`. Первый профиль поддерживает `scope`, `driver=sqlite`, `path`, `timeout_ms`; неизвестные поля и непроверенные options отвергаются. Серверные подключения, TLS, secret references и pools требуют последующих драйверов и conformance.

Отсутствующая секция сохраняет прежние defaults и сериализацию. Настройка остаётся в существующем YAML ConfigStore и не зависит от доступности БД. Проект не переопределяет workplace profile и не получает права через профиль.

Смена профиля не переносит данные. Managed store проверяется по `store_id`, владельцу и scope; hot reload не переключает его автоматически. Старые strict parsers отвергнут расширенную конфигурацию: W4 должен согласовать обновление всех readers и восстановление прежних config bytes.

Предлагаемые конечные пути для общего freeze:

- workplace: `data/pf.sqlite3`;
- project: `.pf/data/pf.sqlite3`, через фактический flow root;
- поиск: отдельное существующее производное хранилище.

Это предложения, текущие пути не изменены. Активация новой operational DB при сохранении независимой основной accounting DB не считается завершённой консолидацией. До подтверждённого переноса затронутых владельцев foundation остаётся неактивной.

**Схема и взаимодействие**

Для основной БД предлагаются один storage-envelope и две служебные таблицы:

- `pf_store_meta`: identity, scope, owner, format version;
- `pf_schema_versions`: namespace, version, checksum.

`application_id/user_version` принадлежат физическому envelope; доменные версии учитываются отдельно. Префиксы `accounting_`, `events_`, `hooks_`, `execution_` исключают коллизии. Неизвестная, будущая или неполная схема отвергается без исправления при открытии.

W1 фиксирует владельцев фактов и repository-порты; W3 — execution schema, индексы, fencing и active-only запросы; W4 — checkpoints, barriers, backup и единственный момент переключения писателей. Общий драйвер не создаёт второй источник канонического состояния задач и не обещает общую транзакцию нескольких БД.

**Implementation-map**

`implementation-map.json` содержит точные API-сигнатуры, 19 хешей исходников, зависимости, проверки и предложение владения 39 файлами:

- **W2:** новый `database/**`, модели профилей, две configuration schemas, будущие `tests/database/**` и документация API.
- **W1:** accounting repository/service/composition, проектные журналы и legacy helper.
- **W3:** execution repository и SQLite adapter; конкретные runtime-потребители уточняются его картой.
- **W4:** существующие maintenance/import/update owners.
- **Один последовательный интегратор:** общие composition/bootstrap, CLI/MCP/Runtime и config resolution.

Пересечений предложенного владения файлами нет. Распределение требует общего freeze и отдельных implementation scopes.

SHA256 карты: `3bf8e7635e8216e3bdbccb4fa52bc1788bfab1f14d012e9fd949f8041b041bea`.

**Проверки и ограничения**

Структурная проверка PowerShell (`ConvertFrom-Json`, `Get-FileHash`, `Group-Object`, `Select-String`) завершилась с exit `0`: JSON корректен, 19 исходников сохранили хеши, повторных владельцев и абсолютных приватных путей в карте/логе нет.

После реализации необходимы проверки транзакций, конкуренции, snapshot, типов, redaction, схем и config compatibility; существующие accounting/maintenance регрессии; реальные CLI/MCP/file-only сценарии; 0/~510/400000 завершённых исполнений с измерением active-only запросов. Затем применимые PF Python QA и независимое ревью.

Тесты и функциональные проверки здесь не запускались: изменены только design artifacts. Совместимость и производительность ещё не доказаны.

Serena обнаружена у host, но не разрешена prepared grants `mcp=[]`; использована ограниченная shell-навигация. Некоторые временные каталоги тестов недоступны, `pyproject.toml` отсутствует. Использованы разрешённые локальные Python материалы о Protocol, dataclasses и docstrings; SQLite-гарантии нового API требуют исполнения conformance.

READ_ACK/RESULT_READY и Ledger heartbeat не отправлялись: разрешённая запись ограничена W2 artifacts/scratch. Координационная доставка остаётся за оркестратором. Новый Work, изменение lifecycle, продуктовые правки, миграции, коммиты и push не выполнялись.