# Основа SQL API

`processforge_core.database` предоставляет синхронный SQL API. Импорт, создание
объектов и `DatabaseFactory.from_profile` не подключаются к БД и не создают файлы.
Единственный драйвер — SQLite; SQL использует его диалект и параметры `?`.

Host composition разрешает относительный профиль от фактического flow root,
проверяет containment, включая symlink/reparse escape, и передаёт разрешённый
абсолютный `DatabaseTarget`. Неперсистентный профиль проекта по умолчанию —
`data/pf.sqlite3`. Профиль не даёт доступа. Cold factory проверяет структуру и
scope; повторно вывести отсутствующий base она не может. Binding закрепляет путь
и store_id; перезагрузка конфигурации не переключает работающий execution target.
Хранилище workplace этим этапом не активируется.

`read()` открывает существующую БД read-only и snapshot. `transaction()` использует
существующую БД и `BEGIN IMMEDIATE`: успех фиксирует изменения, любой
`BaseException`, включая ошибку commit, откатывает транзакцию. Контексты закрывают
соединения и курсоры, не создают отсутствующую БД и не повторяют операции.
Сессия привязана к операции и потоку; строки неизменяемы и отделены от курсора.
При ранней остановке stream требуется выйти из его контекста. Размер пакета —
1–1000, execute-many — до 10000 строк с пустыми statement.params. Значения:
None/int/float/str/bytes; bool, переполнение int64, NaN/Infinity запрещены.

Deadline задаётся абсолютным `time.monotonic()`. Busy timeout ограничен оставшимся
бюджетом, progress handler прерывает длинный запрос. `DatabaseError` содержит код
и retryable без SQL, параметров, нативных ошибок и частного пути. Не держите
транзакцию во время Popen/wait, сигналов, чтения вывода, проекции, backup или scan.

Только SchemaManager выполняет административный DDL/PRAGMA. `inspect()` ничего не
создаёт; store_id=None допустим лишь для discovery с проверкой scope/owner и
application_id. Для обычных read/write нужен конкретный UUID hex store_id.
`initialize()` требует отсутствующий файл; ошибка оставляет заблокированный
неинициализированный target для явного обслуживания. `apply()` атомарно добавляет
отсутствующий namespace и checksum; совпадение version/checksum ничего не меняет,
upgrade/drift/future version отклоняются. Checksum — `sha256:` + SHA256 canonical
JSON `{namespace,version,statements}`: UTF-8, sort_keys, compact separators,
ensure_ascii=False, allow_nan=False, без завершающего перевода строки.
Envelope: application_id `0x50464D31`, user_version 1; identity проверяется перед
domain access. Администрирование задаёт WAL, записи проверяют FULL и FK=ON.
Публичные сессии запрещают административные SQLite opcodes; это API доверенных
репозиториев, без обещания sandbox для произвольного недоверенного SQL.

Необязательная секция `database` содержит profiles/defaults. Профиль: scope,
driver=sqlite, относительный path, timeout_ms (точный int 0–30000, default 100).
ID соответствует `[a-z][a-z0-9_-]{0,63}`. Неизвестные параметры, небезопасные пути
и некорректные defaults отклоняются; mapping неизменяемы. Project overrides
разрешают только project profiles/project_main, без коллизий имён и изменения
workplace-профилей. При отсутствии секции старые сериализация/get/update/reset
сохраняют отсутствие database. Legacy accounting/events/hooks не перенаправляются.


## Native transport и выбор настроек

`DatabaseFactory.resolve_driver(config=None)` — cold closed mapping sqlite.
`SQLiteDriver._connect(database, *, timeout=5.0, isolation_level='', uri=False)`
передаёт прежние native options без изменений. Connection lifetime/errors
принадлежат адаптеру; seam не выполняет mkdir, PRAGMA, BEGIN или migration.
Main `_admin` использует его с прежними строгими envelope/deadline/error checks.
Legacy domains сохраняют пути/schema/application IDs; DI adapters подключает
их владелец отдельно.

`STORE_ENVELOPE_DDL` экспортирует ровно две прежние statements без изменения
bytes для additive UUID migration распознанных stores. Main UUID/owner/scope,
application ID и namespace checks не ослаблены; legacy не принимается как main.
Wildcard UUID доступен только noncreating SchemaManager.inspect.

`DatabaseConfig.driver` независим от profiles: absent/null означает sqlite.
Host получает полный snapshot через ConfigurationProvider и передаёт
resolve_driver(snapshot.config.database). Transport не читает config сам.
Profile не выдаёт permissions; containment/binding проверяет host. Refresh не
переключает уже закреплённый UUID/path без maintenance.
