# Отдельный поиск и фактическая готовность DB-адаптеров

Результат: решение оператора об отдельной поисковой базе записано; готового
переключения SQLite/MariaDB/PostgreSQL в Core нет. Реализация исходной DB-задачи
не запускалась. Новая ревизия дополняет исходный spec и сохраняет историю.

## Задание, scope и контекст

Оператор окончательно выбрал отдельную поисковую базу и спросил о готовности
SQL-адаптеров. Planning-only successor имеет valid/ready immutable capsule,
точного predecessor, один writer и только read/write_artifact. Разрешены новые
документы и обновление mutable current-requirements.json. Старые требования,
карточка DB-задачи, исходники и capsules не изменяются. Реализация, миграция,
настройки БД, индекс, зависимости, Runtime/MCP и будущий RAG вне scope.

## Investigation и impact

Serena проверила AccountingService.__init__, WorkplaceAccounting.service,
sqlite_storage и ResourceIndexBackend; дополнительно прочитаны committed
origin/dev blobs и локальная документация resource-search-index/spec.

- AccountingService принимает конкретный SQLiteAccountingRepository.
- WorkplaceAccounting.service прямо создаёт SQLiteAccountingRepository
  либо его SQLite read-only subclass. Общего выбора SQL-драйвера здесь нет.
- sqlite_storage предоставляет SQLite transaction/metadata/database helpers.
- ResourceIndexBackend задаёт mark_dirty/refresh/rebuild/maintenance_tick
  для поискового индекса. Это не API подключений/транзакций SQL.
- Поиск MariaDB/PostgreSQL/SQLAlchemy/PyDAL и generic DB adapter names в Core
  не выявил реализованных альтернативных SQL-backends. Исходная DB-spec
  по-прежнему явно отмечает, что выбор библиотеки и реализация не начаты.

Наличие DI и Protocol у отдельных компонентов не равно готовности сменить
SQL backend. Проверка подтверждает структуру исходников и опубликованной dev
ветки; живое переключение БД и backend conformance не выполнялись. Хеши
файлов/committed blobs и пределы поиска записаны в adapter-readiness.json.

## Domain, архитектурное решение и план

Основная SQL-база рабочего места, проектная база в `.pf` и отдельное поисковое
хранилище имеют разные владельцев и жизненные циклы. Принята именно топология;
полный DAL, SQL drivers, migration design и будущий retrieval/RAG ещё требуют
отдельных этапов. Поиск не должен размещаться в основной бухгалтерской базе.
Текущий отдельный FTS5 остаётся на месте; новые файлы БД не создаются.

План этой Work: сохранить предыдущий current-reference приватно; добавить
requirements/report/adapter-readiness; обновить текущий указатель с digest;
проверить ссылки, JSON, факты scope и сохранность inputs/index; пройти native
planning lifecycle и доставить собственные документы в оба dev remote.

## Изменение и assurance

Выполнены только плановые документы и append-only log. Проверка validation.json
фиксирует JSON/ссылки/whitespace, digest новой ревизии, separate-search flags,
честный статус SQL adapter readiness и неизменность исходников/старых inputs/
capsule/snapshot/main index. Product pytest/Ruff/mypy/browser checks неприменимы:
нового исполняемого продуктового кода нет. Собственная проверка primary не
объявляется независимым review; planning-only requires_review=false.

## Delivery и evolution

Product release/build/install/migration profile неприменим. Только документы
фиксируются и отправляются в origin/dev и gitverse/dev; GitVerse через TOKEN,
полный SHA читается обратно. До исполнения push delivery не объявляется
состоявшейся. Native run/capsule doctors и completion фиксируются отдельно.

В будущей DB Work читать current-requirements.json и эту ревизию вместе со
старой spec. Поиск теперь обязательно отдельный; backend-neutral SQL adapter
слой остаётся будущей работой. Фиксация решения не означает завершение R02/R12,
создание RAG-задачи, SQL-драйверов, migration или agent scheduler. Оригинальная
DB-карточка остаётся open; память и immutable процессные документы не меняются.
