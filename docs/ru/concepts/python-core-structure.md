# Структура Python-Ядра

Ядро развивается поэтапно. `tools/processforge.py` остаётся действующим legacy facade, а не удалённым кодом. CLI, MCP, hooks и aliases bootstrap сохраняются.

## Текущие Обязанности

| Модуль | Обязанность |
| --- | --- |
| `src/processforge_core/garage.py` | Сервисы проекта, контекста и чтения текущей работы, включая `CurrentWorkService`. |
| `src/processforge_core/process_execution.py`, `continuation.py` | Управляемый lifecycle, выбор работы, pinned execution, evidence, завершение и восстановление. |
| `src/processforge_core/work_state.py` | Чистые правила требований завершения и action/blockers состояния Work, без ввода-вывода и полномочий на переход. |
| `src/processforge_core/document_store.py`, `work_inventory.py` | Чтение YAML и актуальный отсортированный обход без общего изменяемого кеша документов. |
| `src/processforge_core/work_records.py` | Чтение актуальных Run/Assignment; выбор работы и восстановление остаются в прикладном сервисе. |
| `src/processforge_core/work_context_read.py` | Прежние проверки капсулы и нормализация Assignment с явно переданными функциями путей и проверки. |
| `src/processforge_core/process_definition_read.py` | ??????? ?????? effective ProcessDefinition ? pin status ? ???? ??????????? resolver/fingerprint. |
| `src/processforge_core/ports.py` | Внутренние типизированные зависимости чтения текущей работы, записей Work и контекста. |
| `src/processforge_core/composition.py` | Общие фабрики сервисов и узкие адаптеры чтения и контекста legacy-модуля. |
| `src/processforge_core/bootstrap.py` | Существующая сборка runtime-модулей и ленивый доступ к фабрикам сервисов. |
| `tools/processforge.py`, `tools/pf_runtime/` | Legacy CLI facade, транспортные адаптеры, host и provider policies. |

`build_current_work_service(project_root, port)` создаёт прежний сервис с любой структурно подходящей зависимостью, без загрузки CLI и без ввода-вывода при сборке. `RuntimeBootstrap.current_work_service(project_root)` использует уже загруженное ядро через `LegacyWorkReadAdapter`. Глобальный реестр сервисов, общий кеш и DI-контейнер не вводятся.

Конструктор `CurrentWorkService(project_root, core)` и путь класса сохранены. Порядок обхода, fallback отсутствующего assignment, исключение bootstrap placeholders, форма summary и обработка ошибок не меняются. Прежним потребителям не требуется немедленная миграция.

`build_process_execution_service(project_root, workplace_root, core, *, observer=None, records=None, context=None, definitions=None)` используется CLI, MCP и Host/Daemon. Метод `RuntimeBootstrap.process_execution_service(...)` вызывает ту же фабрику. Сборка не загружает CLI, не выбирает проект, не читает конфигурацию и не выполняет ввод-вывод. Прежний конструктор `ProcessExecutionService` с тремя аргументами сохранён; дополнительные зависимости передаются только по имени и не входят в equality/repr. Оставшиеся зависимости от legacy явные, без универсального интерфейса Core.

`WorkRecordReadPort` содержит `runs`, `load_run` и `load_assignment`. По умолчанию фабрика подключает `YamlWorkRecordReader` на существующих `WorkInventory` и YAML loader. Пути и документы читаются актуальными, общего кеша между запросами нет. Прямой старый конструктор сохраняет прежний обход и private path helpers, включая переопределения в подклассах. Читатель не выбирает Work, не скрывает дубликаты и aliases и не решает вопросы восстановления.

`WorkContextReadPort` содержит `validation` и `normalized_assignment`. Сборка по умолчанию выполняется лениво через `build_work_context_read_service`: используются функции путей вызывающего сервиса и узкий `LegacyWorkContextAdapter`. `WorkContextReadService` не зависит от монолитного ядра: четыре зависимости определяют пути, проверяют контракт и нормализуют Assignment. Прежние правила `work_context.py` сохраняют signed identity/intent, pins, scope и stage views. Лимиты байтов, запрет symlink/выхода за root, checksum исходных байтов, безопасный разбор и порядок ошибок сохранены. Сборка не захватывает документ, root или Logger; проверки и нормализация получают актуальные данные.

`ProcessDefinitionReadPort` ???????? `effective_process(run)`. `ProcessDefinitionReadService` ???????? ??????? ?????????? ???????? ???????? ? ?????????? ????????????? fingerprint. ?? ????????? `_effective_process` ?????????? ?????? ????? `build_process_definition_read_service` ? ????? `LegacyProcessDefinitionAdapter`. ?????????? ? ???????????? pin ???????? ??? ????????; legacy-??????????? ??????????? ????????? ??? ?????? ??????. ???????????? ??????????? ????? ?? ????? ???????????? ??????. ????????? ??????? `pinned`, `corrupt`, `legacy_unpinned`, `missing` ? ??????? ??????? ??????. ???????? ?? ???????? ???????, ?? ??????? pin ? ?? ????????? ???????; ??????? ? ????????? legacy-??????????? ????????.

`ProcessExecutionService.state()` сохраняет точный выбор Work, проверки контекста и pins, evidence/outcomes и готовность полномочий. `WorkStatePolicy` отдельно вычисляет требования завершения и action/blockers по переданным записям. Она не читает файлы, не меняет записи, не выбирает caller identity и не переводит процесс. Приоритеты конечного состояния, завершения, блокировки и незавершённости прежние; execution_readiness остаётся отдельным полем ответа.

## Диагностика

Чтение Work state использует существующие PF operation, validation span и ограниченные счётчики request/YAML. Для библиотечного вызова можно передать существующий `diagnostics.Logger` как observer либо использовать текущую operation. Без обоих действует no-op: диагностические файлы не создаются. При сборке сервис не захватывает текущий Logger или Work.

Выбранные run/assignment/stage привязываются внутри операции чтения и восстанавливаются после неё, включая ошибки. Сохраняются фильтры профилей, срок действия, лимиты и обработка сбоя sink. Operation-completed означает возврат из чтения, а не успех Task; предметное действие не меняется. Замеры времени и spans не являются CPU- или memory-профайлером.

CLI/MCP сохраняют внешнюю диагностику и проверки доступа. Host использует ту же инструментированную службу, но автоматически не включает файловый логгер: без внешнего observer остаётся no-op. Диагностика IPC/scheduler Daemon и generic worker требует отдельных ограниченных задач. Initialization, denied и status preflight не получают неявную запись журналов.

## Границы

Порты и фабрика пока внутренние, предварительные интерфейсы, а не расширение стабильного публичного API пакета. `Protocol` описывает зависимость для проверки типов, но не выдаёт права и не проверяет grants. Порт чтения не содержит переходов или записи состояния.

Остальные сервисы ещё зависят от legacy core. Целевая структура: предметные правила, прикладные сервисы, инфраструктурные адаптеры и тонкие транспорты с явной сборкой. Полное выделение этих слоёв ещё не выполнено. Исторические форматы, pinned capsules, защитные отказы и доверенные provider boundaries должны сохраняться.

`tools/smoke_core_read_composition.py` проверяет прежнее поведение, подмену порта, поля bootstrap, делегирование и изолированный пакет в структуре установки без CLI. Такая fixture не является приёмкой установленного Core или подключённого хоста. Проверки исходников, архива, установки и connected host разделены.

`tools/smoke_core_work_state.py` проверяет выделенные правила, семантику состояния, сборку без ввода-вывода, профили/ошибки/изоляцию observer и делегирование CLI/MCP/Host. Необязательный `--baseline` сравнивает сохранённый исходный метод; `--scratch-root` ограничивает временные fixtures. Проверка изолированного пакета подтверждает импорты и сборку в структуре установки, но не действующую установку или подключённый Daemon.

`tools/smoke_work_record_read_composition.py` проверяет подмену записей, актуальное чтение YAML и совместимость выбора Work. `tools/smoke_work_context_read_composition.py` проверяет подмену контекста, защитные отказы капсул, нормализацию/readiness, актуальность чтения и диагностику. Сохранённые исходные методы подтверждают паритет, но не приёмку установленного Core. Репозитории snapshot, атомарная запись/восстановление и остальные legacy-сервисы требуют отдельных ограниченных срезов.

`tools/smoke_process_definition_read_composition.py` ????????? pins, ?????? ??????, ???????????, ?????????? legacy resolver, ????????? ??????????? ? ?????? ??? ?????-??????. ????? ??????????? state guard ? ????????????? ????????? ?????? ??? CLI; `--baseline` ?????????? ??????????? ??????? ?????, `--scratch-root` ???????????? ????????? ?????. ??? ???????? ?????????? ? ??????, ?? ??????? ????????? ?????????????? Core.
