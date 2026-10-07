# Структура Python-Ядра

Ядро развивается поэтапно. `tools/processforge.py` остаётся действующим legacy facade, а не удалённым кодом. CLI, MCP, hooks и aliases bootstrap сохраняются.

## Размещение По Пакетам

Новые модули реализации размещаются в пакетах по ответственности согласно
[правилу ядра](../../../src/processforge_core/AGENTS.md). Имена пакетов — короткие
и в нижнем регистре, модулей — `snake_case.py`, классов — `CapWords`. Модуль может
содержать службу, её исключения и связанные вспомогательные функции; обязательного
соответствия «один класс — один файл» нет. Дерево пакетов должно быть неглубоким,
а `__init__.py` — минимальным.

Существующие Work-модули перенесены в `processforge_core.work`: `context`,
`context_read`, `inventory`, `records`, `resources`, `resource_material`,
`selection`, `state`, `boundary_advisory`, `transition_commit`, `automation_readiness`,
`transition_rejection`. Например,
`WorkResourceService` импортируется из `processforge_core.work.resources`.
Текущие потребители Core/CLI/MCP/Host переведены на эти пути. Старые плоские
Work-импорты на текущем dev-этапе не сохраняются.

Сборка/bootstrap, общие точки входа и оставшиеся прежние модули пока находятся в
корне. Следующие группы ответственности переносятся отдельными ограниченными Work.
Используются обычные Python-пакеты; слой совместимости импортов и новый loader
не добавляются.

Подготовка инструкций входа агента собрана в `processforge_core.agent_entry`:
`contract`, `migration`, `profiles`, `adapters`, `start_prompt`. Например,
`load_contract` импортируется из `processforge_core.agent_entry.contract`.
Инициализация проекта, CLI и существующие проверки используют новые импорты;
старые плоские entry-модули на текущем dev-этапе удаляются. Пакет объединяет
существующие реализации, сохраняя форматы инструкций, поведение команд и
защитные проверки транзакций.

Службы завершения Run размещены в `processforge_core.completion`: `policy`,
`documents`, `intent_builder`, `intent_read`, `intent_validation`, `intent_replay`.
Например, `CompletionIntentReadService` импортируется из
`processforge_core.completion.intent_read`. Сборка и выполнение процесса используют
новые импорты; старые плоские completion-модули на текущем dev-этапе удаляются.
Существующие классы, отложенная сборка, форматы журнала и порядок восстановления
сохраняются. Решения о жизненном цикле, защитные проверки и блокировки Run остаются
у координатора процесса.

Чтение определения процесса, выбор из предложенных процессов и подготовка pin
размещены в существующем пакете `processforge_core.process_catalog`:
`definition_read`, `selection`, `pin`, рядом с `models` и `service`. Например,
`ProcessDefinitionReadService` импортируется из
`processforge_core.process_catalog.definition_read`. Сборка, выполнение процесса
и существующие проверки используют новые импорты; старые плоские пути модулей
на текущем dev-этапе удаляются. Прежние правила, явные зависимости и чтение
актуальных данных сохраняются; допуск к работе и управление жизненным циклом
остаются у координатора процесса.

Проекции готовности автоматизации и правила восстанавливаемого отказа перехода
размещены в `processforge_core.work.automation_readiness` и
`processforge_core.work.transition_rejection`. Например, `AutomationReadinessService`
импортируется из `processforge_core.work.automation_readiness`. Сборка, выполнение
процесса и существующие проверки используют модули по их ответственности; старые
плоские пути на текущем dev-этапе удаляются. Существующие классы целиком, неизменяемые
зависимости и отложенная сборка сохранены. Защитные проверки жизненного цикла,
блокировки, форматы ответов и восстановление остаются у прежних владельцев.

Правила сбора и проверки доказательств, а также готовности этапа размещены в
`processforge_core.evidence`: `collection`, `validation`, `readiness`. Например,
`EvidenceValidationService` импортируется из `processforge_core.evidence.validation`.
Сборка, выполнение процесса и существующие проверки используют модули по их
ответственности; старые плоские пути на текущем dev-этапе удаляются. Существующие
реализации целиком, неизменяемые зависимости, актуальная диагностика файлов и
отложенная сборка сохранены. Полномочия на переход, защитные проверки, блокировки
и восстановление остаются у координатора процесса.

## Текущие Обязанности

| Модуль | Обязанность |
| --- | --- |
| `src/processforge_core/agent_entry/` | Контракт входа, профили, клиентские адаптеры, стартовая подсказка, защищённое размещение инструкций и восстановление. |
| `src/processforge_core/completion/` | Правила завершения Run, итоговые документы и индекс задач, подготовка, чтение, проверка и восстановление по записи о завершении. |
| `src/processforge_core/evidence/` | Прежние правила сбора и identity доказательств, нормализация и актуальная диагностика файлов, удовлетворение требований и gates, порядок blockers готовности через явные зависимости. |
| `src/processforge_core/garage.py` | Сервисы проекта, контекста и чтения текущей работы, включая `CurrentWorkService`. |
| `src/processforge_core/process_execution.py`, `work/continuation.py` | Управляемый lifecycle, выбор работы, pinned execution, evidence, завершение и восстановление. |
| `src/processforge_core/work/state.py` | Чистые правила требований завершения и action/blockers состояния Work, без ввода-вывода и полномочий на переход. |
| `src/processforge_core/work/automation_readiness.py`, `work/transition_rejection.py` | Прежние проекции готовности автоматизации, чтение актуальных событий Assignment и правила ответа при восстанавливаемом отказе перехода через явные зависимости. |
| `src/processforge_core/documents/reader.py`, `work/inventory.py` | Чтение YAML и актуальный отсортированный обход без общего изменяемого кеша документов. |
| `src/processforge_core/work/records.py` | Чтение актуальных Run/Assignment; выбор работы и восстановление остаются в прикладном сервисе. |
| `src/processforge_core/work/context_read.py` | Прежние проверки капсулы и нормализация Assignment с явно переданными функциями путей и проверки. |
| `src/processforge_core/process_catalog/` | Модели и разрешение каталога, чтение effective ProcessDefinition, выбор из предложенных процессов и подготовка pin через явные зависимости. |
| `src/processforge_core/project/snapshot.py` | Чтение актуального ProjectContextSnapshot и checksum исходных байтов через переданные функции пути, загрузки и хеширования. |
| `src/processforge_core/project/initialization.py` | Прежние подготовка проекта, состояние и восстановление с использованием защищённых операций размещения инструкций. |
| `src/processforge_core/resources/local_search.py` | Прежние локальный индекс и поиск ресурсов, проверка доступной области и правила индексирования. |
| `src/processforge_core/runtime/metrics.py` | Существующий сбор Runtime metrics с бюджетами, registered project roots, freshness и collection workers; импорт из `processforge_core.runtime.metrics`. |
| `src/processforge_core/maintenance/update.py` | Существующие plan, контролируемый apply, status и recovery Core update с прежними manifest и backup guards; импорт из `processforge_core.maintenance.update`. |
| `src/processforge_core/prepared/input.py`, `prepared/resources.py` | Существующие immutable prepared inputs, манифесты worker attempts, авторизованные материалы ресурсов и collection receipts; импорты из `processforge_core.prepared.input` и `processforge_core.prepared.resources`. |
| `src/processforge_core/ports.py` | Внутренние типизированные зависимости чтения текущей работы, записей Work и контекста. |
| `src/processforge_core/composition.py` | Общие фабрики сервисов и узкие адаптеры чтения и контекста legacy-модуля. |
| `src/processforge_core/bootstrap.py` | Существующая сборка runtime-модулей и ленивый доступ к фабрикам сервисов. |
| `tools/processforge.py`, `tools/pf_runtime/` | Legacy CLI facade, транспортные адаптеры, host и provider policies. |

`build_current_work_service(project_root, port)` создаёт прежний сервис с любой структурно подходящей зависимостью, без загрузки CLI и без ввода-вывода при сборке. `RuntimeBootstrap.current_work_service(project_root)` использует уже загруженное ядро через `LegacyWorkReadAdapter`. Глобальный реестр сервисов, общий кеш и DI-контейнер не вводятся.

Конструктор `CurrentWorkService(project_root, core)` и путь класса сохранены. Порядок обхода, fallback отсутствующего assignment, исключение bootstrap placeholders, форма summary и обработка ошибок не меняются. Прежним потребителям не требуется немедленная миграция.

`build_process_execution_service(project_root, workplace_root, core, *, observer=None, records=None, context=None, definitions=None, snapshots=None)` используется CLI, MCP и Host/Daemon. Метод `RuntimeBootstrap.process_execution_service(...)` вызывает ту же фабрику. Сборка не загружает CLI, не выбирает проект, не читает конфигурацию и не выполняет ввод-вывод. Прежний конструктор `ProcessExecutionService` с тремя аргументами сохранён; дополнительные зависимости передаются только по имени и не входят в equality/repr. Оставшиеся зависимости от legacy явные, без универсального интерфейса Core.

`WorkRecordReadPort` содержит `runs`, `load_run` и `load_assignment`. По умолчанию фабрика подключает `YamlWorkRecordReader` на существующих `WorkInventory` и YAML loader. Пути и документы читаются актуальными, общего кеша между запросами нет. Прямой старый конструктор сохраняет прежний обход и private path helpers, включая переопределения в подклассах. Читатель не выбирает Work, не скрывает дубликаты и aliases и не решает вопросы восстановления.

`WorkContextReadPort` содержит `validation` и `normalized_assignment`. Сборка по умолчанию выполняется лениво через `build_work_context_read_service`: используются функции путей вызывающего сервиса и узкий `LegacyWorkContextAdapter`. `WorkContextReadService` не зависит от монолитного ядра: четыре зависимости определяют пути, проверяют контракт и нормализуют Assignment. Прежние правила `work/context.py` сохраняют signed identity/intent, pins, scope и stage views. Лимиты байтов, запрет symlink/выхода за root, checksum исходных байтов, безопасный разбор и порядок ошибок сохранены. Сборка не захватывает документ, root или Logger; проверки и нормализация получают актуальные данные.

`ProcessDefinitionReadPort` предоставляет `effective_process(run)`. `ProcessDefinitionReadService` получает прежний resolver определения процесса и существующую функцию fingerprint. По умолчанию `_effective_process` использует ленивую сборку через `build_process_definition_read_service` и узкий `LegacyProcessDefinitionAdapter`. Для валидных и повреждённых pin каталог не читается; legacy определения разрешаются заново при каждом вызове. Возвращаемые копии сохраняют неизвестные поля. Прежние статусы `pinned`, `corrupt`, `legacy_unpinned`, `missing` и границы обработки исключений сохранены. Reader не выбирает процесс, не создаёт pin и не разрешает переходы; остальные зависимости от legacy остаются.

`ProjectSnapshotReadPort` предоставляет `load(path=None)` и `checksum(path)`. Стандартный `ProjectSnapshotReadService` собирается лениво через `build_project_snapshot_read_service` и `LegacyProjectSnapshotAdapter`, сохраняя прежний YAML loader и переопределения `_flow_root`/`_sha256_file`. Создание pin передаёт один захваченный путь загрузке и checksum; selected resources, preflight и capsule capture загружают актуальный документ отдельно. Отсутствующий файл даёт пустой checksum; ошибки загрузки и хеширования сохраняют прежний порядок. Нового кеша нет. Проверки generation в `work/context.py` остаются прежними; validator сравнивает закреплённые metadata capsule и не получает новую зависимость чтения текущего снимка.

`ProcessExecutionService.state()` сохраняет точный выбор Work, проверки контекста и pins, evidence/outcomes и готовность полномочий. `WorkStatePolicy` отдельно вычисляет требования завершения и action/blockers по переданным записям. Она не читает файлы, не меняет записи, не выбирает caller identity и не переводит процесс. Приоритеты конечного состояния, завершения, блокировки и незавершённости прежние; execution_readiness остаётся отдельным полем ответа.

`ProjectContextService` также принимает keyword-only зависимость `snapshots`. Его чтение снимка и совместимый двухаргументный Garage helper `load_snapshot` переиспользуют существующий reader через `build_project_context_snapshot_read_service`. Прежние resolver пути и YAML loader вызываются в исходном порядке при каждом стандартном чтении; ошибки неправильной пары путей и загрузки передаются без изменений. Сборка не делает I/O, а legacy чтение не требует checksum callback. Существующие MCP потребители контекста используют `build_project_context_service` после session/project guards. Freshness checks, payload контекста, request scope и остальные legacy зависимости Garage остаются у прежних владельцев; композиция не даёт полномочий.

`ResourceSearchService` принимает тот же keyword-only порт `snapshots`. Default чтение для readiness coverage и поиска использует совместимый Garage helper; явно переданный пустой snapshot по-прежнему исключает загрузку. Freshness guard поиска предшествует чтению, а blocked readiness сохраняет существующее чтение для coverage. `build_resource_search_service` собирает существующего MCP потребителя поиска без I/O, после ingress guards. Index maintenance, аргументы запроса, navigation, coverage, payload и границы обработки ошибок сохраняют прежнее поведение.

`ResourceResolveService` принимает keyword-only порт `snapshots` через тот же helper. Пустой идентификатор ресурса по-прежнему возвращает сведения о проекте без чтения снимка. `build_resource_resolve_service` собирает MCP resolver без I/O после существующих проверок привязки и freshness. Порядок выбора, aliases, denied results, разрешение path reference и private navigation сохраняют своё поведение. Host использует совместимый конструктор этого общего сервиса; его routing не меняется.

`GarageModeService` использует тот же keyword-only порт чтения. Существующий fallback `snapshot or ...` сохранён: переданный пустой snapshot вызывает чтение, непустой исключает его. `build_garage_mode_service` собирает существующего потребителя `ProjectContextService.context` без I/O и сохраняет default вызов конструктора с тремя аргументами. Context не передаёт собственный optional reader в mode fallback. Coordination, представление session, blockers и правила mode сохраняют своё поведение; одна session не повышает Garage до Forge.

## Диагностика

`EvidenceCollectionPolicy` выполняет существующие правила сбора current/history evidence, merge и определения identity без I/O или Core. `ProcessExecutionService` сохраняет private facade methods и явно передаёт свои current/identity callbacks для совместимости переопределений в наследниках. Current/history и прежние merge records глубоко копируются; входящие merge records сохраняют исходные ссылки. Поздние input/artifact aliases по-прежнему заменяют прежние записи. Lifecycle и фиксация остаются у прежних владельцев.

`tools/smoke_evidence_collection_policy.py` проверяет сохранённые алгоритмы collection, замену aliases, порядок, семантику копирования/ссылок, переопределения facade и пакет без CLI. `--baseline` сравнивает сохранённый service, `--scratch-root` ограничивает fixtures.

`EvidenceValidationService` выполняет существующие алгоритмы нормализации evidence, проверки безопасного пути и диагностики файла. Неизменяемые зависимости конструктора — корень проекта и явные callbacks часов, относительного пути, hash и необязательного разрешения пути. Factory в composition выполняет только сборку; приватный фасад сохраняет отложенное обращение к Core и переопределения в наследниках. Пути и байты файла проверяются на каждом вызове с прежними diagnostic codes и порядком ошибок.

`tools/smoke_evidence_validation_service.py` проверяет сохранённые результаты и число вызовов, копирование, not_applicable evidence, изменения и удаление файлов, опасные пути, ошибки чтения, identity исключений и сборку пакета без CLI. Поддерживает `--baseline` и `--scratch-root`.

`StageReadinessPolicy` выполняет существующие правила готовности requirements/gates, выбора обязательных артефактов и порядка blockers. Неизменяемые callbacks предоставляют диагностику файла, списки строк, executable stages и вызов blocker через фасад. Policy не выполняет прямой I/O и не получает Core; factory в composition только собирает зависимости. Приватные методы фасада сохраняют aliases, выбор последнего evidence, наборы статусов, приоритет диагностики и семантику копирования/ссылок. Загрузка automation, координация state и фиксация переходов остаются у прежних владельцев.

`tools/smoke_stage_readiness_policy.py` проверяет сохранённые чистые правила, число вызовов и переопределения callbacks, необязательные artifacts/gates, порядок blockers, identity исключений и проверку изменённых/удалённых файлов через общий фасад. Поддерживает `--baseline` и `--scratch-root`.

Чтение Work state использует существующие PF operation, validation span и ограниченные счётчики request/YAML. Для библиотечного вызова можно передать существующий `diagnostics.Logger` как observer либо использовать текущую operation. Без обоих действует no-op: диагностические файлы не создаются. При сборке сервис не захватывает текущий Logger или Work.

Выбранные run/assignment/stage привязываются внутри операции чтения и восстанавливаются после неё, включая ошибки. Сохраняются фильтры профилей, срок действия, лимиты и обработка сбоя sink. Operation-completed означает возврат из чтения, а не успех Task; предметное действие не меняется. Замеры времени и spans не являются CPU- или memory-профайлером.

CLI/MCP сохраняют внешнюю диагностику и проверки доступа. Host использует ту же инструментированную службу, но автоматически не включает файловый логгер: без внешнего observer остаётся no-op. Диагностика IPC/scheduler Daemon и generic worker требует отдельных ограниченных задач. Initialization, denied и status preflight не получают неявную запись журналов.

## Границы

Порты и фабрика пока внутренние, предварительные интерфейсы, а не расширение стабильного публичного API пакета. `Protocol` описывает зависимость для проверки типов, но не выдаёт права и не проверяет grants. Порт чтения не содержит переходов или записи состояния.

Остальные сервисы ещё зависят от legacy core. Целевая структура: предметные правила, прикладные сервисы, инфраструктурные адаптеры и тонкие транспорты с явной сборкой. Полное выделение этих слоёв ещё не выполнено. Исторические форматы, pinned capsules, защитные отказы и доверенные provider boundaries должны сохраняться.

`tools/smoke_core_read_composition.py` проверяет прежнее поведение, подмену порта, поля bootstrap, делегирование и изолированный пакет в структуре установки без CLI. Такая fixture не является приёмкой установленного Core или подключённого хоста. Проверки исходников, архива, установки и connected host разделены.

`tools/smoke_core_work_state.py` проверяет выделенные правила, семантику состояния, сборку без ввода-вывода, профили/ошибки/изоляцию observer и делегирование CLI/MCP/Host. Необязательный `--baseline` сравнивает сохранённый исходный метод; `--scratch-root` ограничивает временные fixtures. Проверка изолированного пакета подтверждает импорты и сборку в структуре установки, но не действующую установку или подключённый Daemon.

`tools/smoke_work_record_read_composition.py` проверяет подмену записей, актуальное чтение YAML и совместимость выбора Work. `tools/smoke_work_context_read_composition.py` проверяет подмену контекста, защитные отказы капсул, нормализацию/readiness, актуальность чтения и диагностику. Сохранённые исходные методы подтверждают паритет, но не приёмку установленного Core. Репозитории snapshot, атомарная запись/восстановление и остальные legacy-сервисы требуют отдельных ограниченных срезов.

`tools/smoke_process_definition_read_composition.py` проверяет pin, форму данных, исключения, актуальность legacy resolver, подмену зависимости и сборку без ввода-вывода. Также проверяются state guard и изолированная структура пакета без CLI; `--baseline` сравнивает сохранённый исходный метод, `--scratch-root` ограничивает временные файлы. Это проверка исходников и fixture, а не приёмка установленного Core.

`tools/smoke_project_snapshot_read_composition.py` проверяет подмену reader во всех четырёх местах чтения, отказ immutable capsule до загрузки, актуальность при одинаковых размере и mtime, checksum исходных байтов, переопределённые пути и хеширование, совместимость конструктора и сборку без CLI. `--baseline` сравнивает сохранённые исходные методы, включая исключения и порядок вызовов; `--scratch-root` ограничивает временные fixtures.

`tools/smoke_garage_snapshot_read_composition.py` проверяет инъекцию reader Garage, актуальность путей, совместимость конструктора, context/runtime payload, порядок ошибок, изоляцию запросов и MCP композицию после ingress guards. Поддерживает сохранённые исходные методы через `--baseline` и ограничивает временные fixtures через `--scratch-root`.

`tools/smoke_resource_search_snapshot_composition.py` проверяет инъекцию чтения readiness/search, ветки пустого snapshot и stale context, порядок maintenance/ошибок, актуальность YAML, request scope, MCP guards/error mapping и пакет без CLI. `--baseline` сравнивает сохранённый исходный service, `--scratch-root` ограничивает fixtures.

`tools/smoke_resource_resolve_snapshot_composition.py` проверяет прежнее поведение resolve, пустые идентификаторы, инъекцию reader, aliases и порядок выбора, актуальность YAML и изоляцию request, порядок MCP guards, совместимость Host и пакет без CLI. `--baseline` сравнивает сохранённый исходный resolver, `--scratch-root` ограничивает fixtures.

`tools/smoke_garage_mode_snapshot_composition.py` проверяет прежнее поведение mode и context, fallback пустого snapshot, инъекцию reader, подмены конструктора, правила session, актуальность YAML и изоляцию request, а также пакет без CLI. `--baseline` сравнивает сохранённый mode service, `--context-baseline` — сохранённого context consumer, `--scratch-root` ограничивает fixtures.

`AutomationReadinessService` выделяет существующую ответственность: готовность автоматизаций и живое чтение последнего события Assignment. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_automation_readiness.py`.

`WorkSelectionService` выделяет существующую ответственность: выбор точной Work, session preference и сопоставление objective. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_work_selection_service.py`.

`ProcessSelectionService` выделяет существующую ответственность: выбор разрешённого процесса и формирование описаний кандидатов. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_process_selection_service.py`.

`ProcessPinReadService` выделяет существующую ответственность: чтение живого snapshot и построение process pin. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_process_pin_read_service.py`.

`RunCompletionPolicy` выделяет существующую ответственность: проверка препятствий завершению Run и изменение статуса задачи в памяти. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_run_completion_policy.py`.

`CompletionIntentValidationService` выделяет существующую ответственность: валидация completion-intent с прежним порядком проверки принадлежности и конечного состояния. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_completion_intent_validation_service.py`.

`TransitionRejectionPolicy` выделяет существующую ответственность: классификация исправимых отказов перехода и построение ответа. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_transition_rejection_policy.py`.

`WorkBoundaryAdvisoryService` выделяет существующую ответственность: рекомендации на границе процессов и поиск advisory handoff. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_work_boundary_advisory_service.py`.

`CompletionDocumentService` выделяет существующую ответственность: формирование summary завершения и публикация существующего task index. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_completion_document_service.py`.

`CompletionIntentBuilder` выделяет существующую ответственность: построение самодостаточного completion-intent до конечных записей. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_completion_intent_builder.py`.

`CompletionIntentReadService` выделяет существующую ответственность: разрешение пути completion-intent и защищённое чтение живого journal. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_completion_intent_read_service.py`.

`CompletionIntentReplayService` выделяет существующую ответственность: упорядоченный replay completion-intent через существующие операции хранения и events. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; решение о восстановлении, блокировки и проверки доступа остаются у прежнего координатора; запись и события выполняются прежними адаптерами. Проверки: `tools/smoke_completion_intent_replay_service.py`.

`WorkTransitionCommitService` фиксирует уже разрешённый переход через явные callbacks существующих операций. Сохранены история этапа, порядок записи Run/Assignment, completion intent/replay, повторное чтение state, проекции, события и рекомендации на границе процесса. `ProcessExecutionService.transition` остаётся владельцем проверок доступа и охватывающей run lock; его конструктор и входы транспортов не меняются. `build_work_transition_commit_service` собирает зависимости без I/O. Проверки порядка публикации, обязательных отказов и поздних переопределений фасада: `tools/smoke_work_transition_commit_service.py`.
