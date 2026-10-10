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
`transition_rejection`, `publication`, `events` и `capsule_publication`. Например,
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
| `src/processforge_core/garage.py` | Чтение текущей Work и оставшиеся legacy helpers; сборка контекста проекта и reconciliation находятся в `project/`. |
| `src/processforge_core/work/projection.py` | Прежние чистые правила проекций и классификации Work, без Core и полномочий lifecycle. |
| `src/processforge_core/work/bootstrap.py` | Прежние guidance/start через явную сводку и отложенную типизированную зависимость запуска. |
| `src/processforge_core/work/creation_scope.py` | Прежние проверка scope и наложение на Assignment через явные отложенные зависимости, без полномочий lifecycle. |
| `src/processforge_core/work/start_documents.py` | Прежнее чистое построение Run/Assignment с сохранением полей и ссылок. |
| `src/processforge_core/work/start_publication.py` | Прежняя упорядоченная публикация запуска после capsule через отложенные зависимости операций. |
| `src/processforge_core/work/continuation_read.py` | Прежнее ограниченное чтение control documents и Continuation/selection paths через явные актуальные зависимости. |
| `src/processforge_core/work/continuation_contract.py` | Прежние проверки версии и привязки записи с явным источником класса ошибки. |
| `src/processforge_core/work/continuation_status.py` | Прежнее актуальное чтение waiting/status/selected через явные зависимости. |
| `src/processforge_core/work/continuation_publication.py` | Прежние создание и возобновление continuation, порядок блокировок и восстановление маркера сессии через явные актуальные зависимости. |
| `src/processforge_core/work/cancellation_replay.py` | Прежнее восстановление отмены из журнала, атомарная публикация и защита от повторных событий через явные актуальные зависимости. |
| `src/processforge_core/work/continuation_work.py` | Прежнее точное чтение Work Continuation и проверки executable/cancellation через узкие зависимости. |
| `src/processforge_core/work/resource_context.py` | Прежнее чтение закреплённого контекста ресурсов Work через явные зависимости. |
| `src/processforge_core/work/resource_declarations.py` | Прежние правила identifiers, indexing declarations, allowlist overlay и portable references, общие с prepared inputs. |
| `src/processforge_core/work/resource_bindings.py` | Прежняя начальная сборка bounded material bindings и отдельных failure records при создании capsule. |
| `src/processforge_core/work/permissions.py` | Общая чистая функция готовности прав Work. |
| `src/processforge_core/project/reconciliation.py` | Прежняя проекция reconciliation контекста через обязательный отложенный типизированный checker, без Core. |
| `src/processforge_core/project/context.py` | Пять существующих операций ProjectContextService и отдельные readers одного вызова через обязательные типизированные зависимости, без Core. |
| `src/processforge_core/project/context_read.py` | Проверки свежести контекста выполнения и чтение manifest через явные зависимости, без Core. |
| `src/processforge_core/project/mode.py` | Прежний GarageModeService: модель координации через обязательный порт чтения snapshot, без Core. |
| `src/processforge_core/project/reports.py` | Прежний DerivedReportLifecycleService и фиксированные пути отчётов через обязательные snapshot/flow-root зависимости, без Core. |
| `src/processforge_core/process_catalog/summary.py` | Прежнее описание разрешённых процессов с необязательным типизированным resolver, без Core. |
| `src/processforge_core/work/publication.py` | Прежняя атомарная публикация текста/YAML через отложенные зависимости форматирования и записи. |
| `src/processforge_core/work/events.py` | Прежняя структура события Work и последующая диагностика через типизированный динамический emitter. |
| `src/processforge_core/work/capsule_publication.py` | Прежняя неизменяемая публикация capsule с отложенными зависимостями и сохранённым exclusive open. |
| `src/processforge_core/process_execution.py`, `work/continuation.py` | Управляемый lifecycle, выбор работы, pinned execution, evidence, завершение и восстановление. |
| `src/processforge_core/work/state.py` | Чистые правила требований завершения и action/blockers состояния Work, без ввода-вывода и полномочий на переход. |
| `src/processforge_core/work/automation_readiness.py`, `work/transition_rejection.py` | Прежние проекции готовности автоматизации, чтение актуальных событий Assignment и правила ответа при восстанавливаемом отказе перехода через явные зависимости. |
| `src/processforge_core/documents/reader.py`, `work/inventory.py` | Чтение YAML и актуальный отсортированный обход без общего изменяемого кеша документов. |
| `src/processforge_core/work/records.py` | Чтение актуальных Run/Assignment; выбор работы и восстановление остаются в прикладном сервисе. |
| `src/processforge_core/work/context_read.py` | Прежние проверки капсулы и нормализация Assignment с явно переданными функциями путей и проверки. |
| `src/processforge_core/process_catalog/` | Модели и разрешение каталога, чтение effective ProcessDefinition, выбор из предложенных процессов и подготовка pin через явные зависимости. |
| `src/processforge_core/project/snapshot.py` | Чтение актуального ProjectContextSnapshot и checksum исходных байтов через переданные функции пути, загрузки и хеширования. |
| `src/processforge_core/project/initialization.py` | Прежние подготовка проекта, состояние и восстановление с использованием защищённых операций размещения инструкций. |
| `src/processforge_core/resources/local_search.py` | Прежние локальный индекс, SQLite/FTS поиск, поиск проверенного материала Work, coverage и indexing policy helpers. |
| `src/processforge_core/runtime/metrics.py` | Существующий сбор Runtime metrics с бюджетами, registered project roots, freshness и collection workers; импорт из `processforge_core.runtime.metrics`. |
| `src/processforge_core/maintenance/update.py` | Существующие plan, контролируемый apply, status и recovery Core update с прежними manifest и backup guards; импорт из `processforge_core.maintenance.update`. |
| `src/processforge_core/prepared/input.py`, `prepared/resources.py` | Существующие immutable prepared inputs, манифесты worker attempts, авторизованные материалы ресурсов и collection receipts; импорты из `processforge_core.prepared.input` и `processforge_core.prepared.resources`. |
| `src/processforge_core/prepared/snapshot_read.py` | Прежнее чтение закреплённого и текущего снимков prepared resources через обязательные отложенные зависимости. |
| `src/processforge_core/prepared/resource_selection.py` | Прежние правила выбора строк, однозначного сопоставления, immutable bindings и отзыва текущего ресурса. |
| `src/processforge_core/prepared/registry_resources.py` | Прежнее чтение и проверки registry resources templates/tools/MCP через узкие отложенные зависимости. |
| `src/processforge_core/prepared/knowledge_resources.py` | Прежняя проверка материалов knowledge-ресурсов и provenance grants через обязательные отложенные зависимости. |
| `src/processforge_core/project/host_integration.py` | Прежняя ограниченная проверка необязательной интеграции проекта с хостом для подготовки проекта и CLI. |
| `src/processforge_core/common/request_scope.py` | Прежний общий контекст одного запроса для Garage, lifecycle, YAML/capsule readers и MCP с изоляцией снимков и ограниченным кешем. |
| `src/processforge_core/resources/snapshot.py` | Прежние search roots, разрешённая selection, path resolution и private navigation ресурсов; чтение snapshot остаётся в project/snapshot.py. |
| `src/processforge_core/resources/access.py` | ResourceSearchService и ResourceResolveService с узкими типизированными портами чтения: прежние readiness, разрешённые поиск/resolve, navigation и внедрение снимка. |
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

`ProjectContextService` находится в `project/context.py` и не имеет поля Core. Два пути проекта/workplace и обязательные именованные зависимости snapshot/чтения описывают пять прежних операций. `build_project_context_service(project_root, workplace_root, core, *, snapshots=None)` сохраняет сигнатуру потребителей и собирает зависимости без I/O; стандартный reader создаётся только при `None`, поэтому ложный в логическом контексте переданный reader сохраняет identity. Пути, документы и ошибки читаются актуальными, checksum для этих операций не требуется. В начале каждого `context()` четыре фабрики mode/report/process-summary/boundary захватываются до freshness check в отдельный `ProjectContextReaders`; прочие helpers разрешаются в прежних местах использования. Сохранены `scoped_request`, всегда явный workplace, check перед snapshot и отказ от основного чтения при broken check. Mode/Reports используют независимые стандартные readers, а не порт контекста. Runtime resolver получается до вычисления `self.snapshot()`. Все ключи, resource values, порядок вызовов и изменение рекомендации continuation сохранены. MCP вызывает прежнюю фабрику после ingress guards. Старый Garage class/import alias, совместимость конструктора, кеш и новые полномочия не вводятся.

`ResourceSearchService` требует узкий `ResourceSearchReadPort` вместо общего объекта Core и сохраняет необязательное keyword-only внедрение `snapshots`. `LegacyResourceSearchReadAdapter` на границе composition выполняет прежние чтения Core и сохраняет позднее получение вызываемых функций. Явно переданный пустой snapshot исключает загрузку, а falsey внедрённый reader сохраняет свою identity. Freshness guard поиска предшествует чтению, а blocked readiness сохраняет существующее чтение для coverage. `build_resource_search_service` сохраняет опубликованную сигнатуру и собирает существующего MCP потребителя поиска без I/O после ingress guards. Проектный контекст сохраняет прежнюю заменяемую привязку сервиса и передаёт тот же read adapter. Index maintenance, аргументы запроса, navigation, coverage, payload и границы обработки ошибок сохраняют прежнее поведение.

`ResourceResolveService` требует `ResourceResolveReadPort` вместо общего Core и сохраняет необязательный именованный `snapshots`. `LegacyResourceResolveReadAdapter` на границе composition связывает прежние операции ID проекта, снимка и path reference без I/O при сборке. ID читается первым; пустой идентификатор ресурса возвращает сведения о проекте без чтения снимка. Falsey внедрённый reader сохраняется, а стандартное чтение остаётся актуальным. Resolver пути получается до вычисления его reference argument. `build_resource_resolve_service` сохраняет опубликованную сигнатуру и собирает MCP и Host потребителей; прежний порядок MCP binding/freshness guards и Host routing сохранён. Выбор, aliases, denied results, исходные поля ресурса, разрешение пути, private navigation, payload и ошибки прежние. Совместимый конструктор и новые полномочия не вводятся.

`GarageModeService` находится в `project/mode.py` и принимает `(project_root, workplace_root, *, snapshots)` с обязательным `ProjectSnapshotReadPort`, без Core. Зависимость исключена из repr/equality. Прежний fallback `snapshot or ...` сохранён: пустой snapshot вызывает `snapshots.load()`, непустой исключает чтение. `build_garage_mode_service(project_root, workplace_root, core, *, snapshots=None)` создаёт стандартный reader только при `None`, сохраняя falsey reader, и не выполняет I/O. Context не передаёт собственный порт в mode fallback. Координация, session, blockers и политика mode прежние; одной session недостаточно для Forge. Старый конструктор и module alias не сохраняются.

`DerivedReportLifecycleService` и `DERIVED_REPORTS` находятся в `project/reports.py`. Обязательные именованные зависимости `snapshots` и `flow_root` не содержат Core и не читают файлы при сборке. Фабрика создаёт независимый стандартный reader только для `None` и откладывает получение flow root до status. Context не передаёт свой reader. Пустой snapshot по-прежнему вызывает чтение перед flow root; порядок отчётов, пути, timestamps, проверки файлов, прежние исключения и итоговый status сохранены.

`ExecutionProjectReadService` находится в `project/context_read.py`. Обязательные именованные зависимости — пути проекта/workplace, resolver типизированной проверки контекста, resolver document loader и отложенный flow root. Каждая приватная `_context_check`/`_manifest` собирает сервис без I/O и кеша. Execution передаёт workplace явно только при наличии `workplace.yaml`; `ProjectContextService.check` всегда передаёт его явно. Loader получается до переопределяемого `_flow_root`, сохраняя порядок чтения и исключений. Приватные операции, проверки доступа и lifecycle authority остаются у координатора.

`ProcessSummaryReadService` находится в `process_catalog/summary.py`; прежняя Garage-функция `process_summary` удалена без alias. Сохранены выбор из snapshot или manifest, порядок процессов, текущий id/stage count и fallbacks title/purpose/description. Необязательные project/resolver зависимости сохраняют пути без проекта или resolver. Фабрика привязывает provider только при Core не `None`, без I/O. Внутри прежнего `try` каждый resolver получается до преобразования argument в строку; только `OSError`, `ValueError`, `SystemExit` дают прежний fallback.

`FreshSessionBoundaryReadService` находится рядом с `WorkBoundaryAdvisoryService` в `work/boundary_advisory.py`. Обязательные зависимости — путь проекта, узкий двухметодный `WorkReadCorePort` и relative-path callback. Фабрика использует `LegacyWorkReadAdapter` и отложенную lambda для `core.rel`. Governed Work возвращает результат до чтения. Сохранены glob order, timestamp tie, последний пригодный completed handoff, проверка route `is_file`, стабильная дедупликация процессов и запрет возврата к старому handoff при отсутствии маршрута. Его рекомендация `fresh` отличается от прежней advisory-проекции `auto`; Garage helper удалён без alias.

`WorkDocumentPublisher` находится в `work/publication.py` и содержит прежнюю атомарную запись текста/YAML. Обязательные именованные providers получают `_atomic_text` до formatter, сохраняя перехват подклассом и порядок исключений, затем применяют `rstrip()` и ровно один newline. Текст сохраняет mkdir, UUID temporary name, UTF-8 и `Path.replace`, без дополнительных cleanup/fsync/retry. Фабрика не выполняет I/O и не получает Core helpers заранее. Живые `_atomic_yaml`/`_atomic_text` у координатора сохраняют callbacks Continuation/transition/completion/recovery; пути, locks, guards и полномочия остаются у прежних владельцев.

`WorkEventPublisher` находится в `work/events.py` и содержит прежний алгоритм публикации события. Обязательные зависимости — путь проекта, availability callback и provider точного именованного `ProcessEventEmitter`. Сохранены отдельный динамический `hasattr` и последующее получение emitter до вычисления аргументов. Отсутствие emitter возвращает результат до diagnostics; non-callable по-прежнему вызывает ошибку. Payload, assignment path, correlation/event IDs и `blockers or []` прежние. Запись journal предшествует отложенному diagnostics import и существующим select/annotate/emit. Живой `_emit` сохраняет callers; journal storage/security, locks, deduplication и authority не переносятся.

`AssignmentCapsulePublisher` находится в `work/capsule_publication.py`. Обязательные именованные зависимости сохраняют прежний алгоритм immutable capsule; точный `ContextFieldsBuilder` оставляет grants/scope прежнему builder. Сборка не читает файлы. Builder получается из своего модуля при вызове после existing-path guard и snapshot read. Живой `_write_capsule` сохраняет перехват подклассов. Поля/updates, exclusive UTF-8 `open("x")`, cause/remediation `FileExistsError` и relative-path-before-raw-hash return прежние. Обычная атомарная замена, locks и полномочия остаются вне этого publisher.

`ContextReconciliationService` находится в `project/reconciliation.py`. Сервис получает пути проекта/workplace и именованный provider существующего `ProjectContextCheck`, без универсального Core. Фабрика в `composition.py` не выполняет I/O; checker извлекается при каждом вызове `status` до вычисления аргументов. Сохранены порядок причин, признаки безопасного технического обновления и необходимости решения оператора, а также исключения прежнего алгоритма. Внутренний класс удалён из Garage без alias; новые потребители или автоматическое обновление контекста не добавляются.

`GovernedWorkBootstrapService` находится в `work/bootstrap.py`. Обязательные именованные зависимости — получение текущей сводки Work и provider типизированного WorkStart, без универсального Core. Холодная фабрика собирает прежние CurrentWorkService и ProcessExecutionService при вызове; получение start предшествует нормализации параметров. Сохранены guidance, mapping preferred-stage и полномочия прежнего координатора lifecycle. Старый класс/import удалён из Garage без alias; новые маршруты или потребители не добавляются.

`WorkProjectionPolicy` в `work/projection.py` объединяет прежние правила классификации элементов, нормализации objective и краткой проекции активных Run без I/O и Core. Конструктор CurrentWorkService и актуальный обход WorkInventory сохранены; проекции вычисляет локальный сервис без состояния. Прежними остаются порядок статусов/fallbacks, исключение bootstrap, порядок удаления повторов и предел десять элементов. Старые Garage helpers/constants удалены без aliases.

`CreationScopeService` в `work/creation_scope.py` объединяет прежнюю чистую проверку operator envelope и наложение scope на Assignment. Холодная сборка передаёт отложенные нормализацию режима и ограниченное чтение handoff; сохранены deep copy, predecessor coordination metadata, checksum исходных байтов, ошибки и порядок lookup. CLI/MCP вызывают общую каноническую проверку. Identity predecessor, admission/overlap и полномочия публикации capsule остаются у прежних владельцев; публичная schema scope не меняется.

`WorkStartDocumentBuilder` в `work/start_documents.py` строит прежние словари Run/Assignment без I/O и Core. Сохранены поля, timestamps, порядок сокращения title и общие ссылки на pin/specializations. Координатор lifecycle по-прежнему выбирает IDs/process/stage, привязывает sessions/security/scope, проверяет готовность, публикует immutable capsule и владеет writes/locks/events. Schema и публичное поведение запуска не меняются.

`WorkStartPublicationService` в `work/start_publication.py` выполняет прежнюю публикацию после capsule через восемь обязательных отложенных providers методов. Сохранён порядок Run/Assignment/plan/index, четырёх событий, свежего состояния, проекции и ответа created_new. Lookup метода предшествует вычислению аргументов; сборка не выполняет I/O. Admission, locks и полномочия capsule остаются в ProcessExecutionService, существующие атомарные writers/events используются без новой transaction/recovery policy.

`ContinuationRecordReader` в `work/continuation_read.py` выполняет прежнее построение record/selection paths, ограниченное 2 MiB чтение и проверку служебных worker/lease записей через восемь обязательных отложенных источников, без Core. Сохранены decode/dictionary/session правила, terminal worker statuses, wildcard lease predicate, порядок glob/lookup и ошибки. Координатор сохраняет переопределяемые точки read/writer вызовов и полномочия binding/resume/cancel; control loader актуален, сборка ничего не читает.

`ContinuationContractPolicy` в `work/continuation_contract.py` выполняет прежние проверки ID, статуса, точной версии и привязки записи через обязательный отложенный источник класса ошибки. Координатор сохраняет переопределяемую точку проверки и полномочия привязки Work. Общая чистая функция `permission_readiness` находится в `work/permissions.py`; lifecycle start/state использует её без импорта координатора Continuation. Сохранены версии, приоритет ошибок, порядок препятствий, ссылки на списки и внешние результаты.

`ContinuationStatusReadService` в `work/continuation_status.py` выполняет прежние сценарии чтения waiting/status/selected через одиннадцать обязательных отложенных источников операций. Сохранены свежесть discovery, предел 20 кандидатов и 128 артефактов, проверки receipt/version, порядок обращения к зависимостям и результаты. Координатор сохраняет переопределяемые точки вызова, публичный перевод ошибок и полномочия изменения/привязки; холодная сборка не добавляет кеш или права.

`ContinuationWorkReadService` в `work/continuation_work.py` выполняет прежнее точное чтение связи Run/Assignment/Capsule для продолжения и операторской отмены через четырнадцать обязательных отложенных зависимостей и узкие протоколы чтения, без Core. Сохранены executable/terminal flags, повторные обращения, порядок проверок/ошибок, ссылки на результаты и правила identity при отмене. Координатор сохраняет конструктор, переопределяемую точку Work, блокировки, session binding и полномочия изменения/восстановления; холодная сборка не добавляет права или кеш.

`WorkResourceContextReadService` в `work/resource_context.py` выполняет прежнее чтение закреплённого контекста через девять обязательных отложенных зависимостей, без Core. Некорректные селекторы отклоняются до обращения к Core, корню проекта и документам. Сохранены чтение Run/Assignment/Capsule, digest и process/snapshot/resource/stage pins, порядок импорта/вызова execution contract, read scope и ссылки результата. WorkResourceService сохраняет конструктор, ограниченный loader, переопределяемую точку контекста и публичные resource routes; сборка не выполняет I/O.

`ContinuationPublicationService` в `work/continuation_publication.py` объединяет прежние алгоритмы создания и возобновления через двенадцать обязательных отложенных зависимостей, без Core. Сохранены валидация, Work binding, порядок вложенных блокировок, preview/existing/apply, прежняя wait-only обработка v1, запись session selection перед resumed marker, восстановление после OSError и повторные обращения к живым зависимостям. Координатор сохраняет публичные сигнатуры и существующие переопределяемые точки чтения, валидации и status. Холодная frozen сборка не добавляет политику, кеш или формат документа.

`CancellationReplayService` в `work/cancellation_replay.py` выполняет прежнее восстановление отмены из журнала через десять обязательных отложенных источников и узкие протоколы записи, binding и событий, без Core. Сохранены checksum, quiescence, capsule и preimage проверки, повторные обращения, порядок атомарных записей/индекса/событий/проекции/receipt, защита от повторных событий, семантика исключений и ссылок. Координатор сохраняет admission, блокировки, preview, создание журнала, already-applied обработку и переопределяемую точку replay. Холодная frozen сборка не добавляет правила отмены или кеш.

`WorkMaterialReadService` в `work/material_read.py` выполняет прежние два этапа проверки metadata и чтения материала для Work search/resolve через девять обязательных отложенных зависимостей, без Core. Все metadata checks предшествуют созданию budget и любому чтению материала; прежние literal statuses, пять material comparisons, живые root/capture dependencies, проверка operation при каждом capture, deep copies и общие provenance references сохранены. Холодная сборка ничего не читает. WorkResourceService сохраняет selector/grant/freshness/pagination guards, публичные ошибки и coverage, overridable context/search calls и конкретный legacy root callback. Новых полномочий и кеша материала нет.

`ResourceDeclarationPolicy` в `work/resource_declarations.py` объединяет прежние чистые правила identifiers, declared indexing, authoritative allowlist/overlay и portable references для Work и prepared resources. Единственный обязательный отложенный error factory сохраняет тип ошибки caller; политика ничего не читает и не получает Core. Идентичные legacy indexing tables переиспользуются из resource_material.py. Порядок, приоритеты, bounds, глубокие копии, unknown fields и lexical path errors прежние; все consumers используют owning policy без старых helper aliases. Material capture, полномочия и подготовка worker остаются у прежних владельцев.

`ResourceBindingBuilder` в `work/resource_bindings.py` собирает прежние начальные resource bindings через восемь обязательных отложенных providers, без Core и чтения при создании. Действующая функция `build_resource_bindings` сохраняет signature и snapshot import, явно передавая прежние declaration/snapshot/root/material/error операции. Публикация capsule и полномочия Work/prepared чтения остаются у своих владельцев. Пустая selection по-прежнему читает current allowlist; общий budget и буквальная проверка status прежние; отказ одного ресурса позволяет продолжать следующие captures. Ссылки на исходные bindings и final availability semantics сохраняются. Lazy factory только собирает builder; cache и миграция pins при чтении не добавлены.

`PreparedResourceSnapshotReader` в `prepared/snapshot_read.py` читает прежнюю пару текущего и закреплённого снимков при подготовке ресурсов. Семь обязательных отложенных операций сохраняют сопоставление current reads, свежесть, immutable generation pins, checksum fallback, границы исключений и идентичность объектов; служба не получает Core и не хранит cache. Ленивый composition factory ничего не читает. Канонический prepared-resource caller сохраняет решения о доступе, material preparation и bounded YAML guards; старый внутренний snapshot helper удалён.

`PreparedResourceSelectionPolicy` в `prepared/resource_selection.py` объединяет прежние правила выбора строк, однозначного сопоставления, строгой binding schema и отзыва текущего ресурса для knowledge и registry preparation. Три обязательных отложенных matcher/error/status providers устраняют зависимость этих правил от Core. Matcher по-прежнему выбирается для каждой строки, границы исключений и ссылки на исходные строки сохраняются; создание ничего не читает. Оба существующих пути используют каноническую политику, сохраняя grants, material capture, path resolution и прежние полномочия.

`PreparedRegistryResourceReader` в `prepared/registry_resources.py` выполняет прежний общий сценарий templates/tools/MCP preparation через пять обязательных отложенных policy/manifest/resolver/status/error providers. Узкий callable Protocol сохраняет именованный workplace_manifest типа Path | None; reader и lazy factory не получают Core и ничего не читают при создании. Каждая непустая группа сохраняет живые manifest/matcher/resolver reads, порядок отказов, path-reference deep copies и исходные resolution references. Канонический prepared caller сохраняет публичные admission checks и порядок grants; старый внутренний registry helper удалён.

`PreparedKnowledgeResourceReader` в `prepared/knowledge_resources.py` выполняет прежний сценарий проверки knowledge material и provenance grants через девять обязательных отложенных providers. Он использует существующие selection/declaration policies, canonical metadata fingerprint и bounded material capture; два callable Protocol описывают реальные root/capture операции. Reader и lazy factory не получают Core и ничего не читают при создании. Prepared caller сохраняет outer authority и порядок групп; его явный callback пока делегирует root resolution прежнему Work helper. Пустой запрос сохраняет проверки bindings/current allowlist и создание budget. Generation/material checks, границы ошибок, живые зависимости и ссылки в grants прежние. Старые knowledge helper и fingerprint wrapper удалены.

`search_material` в `resources/local_search.py` содержит прежний алгоритм SQLite FTS5 в памяти над уже проверенными документами Work. WorkResourceService сохраняет точку search dispatch и все проверки полномочий/материала; обязательный отложенный error factory сохраняет его тип ошибки без импорта Work в поисковый модуль. SQL, закрытие соединения, цепочки исключений, ранжирование, пагинация и ссылки на результаты/provenance прежние. Общий индекс рабочего места и его обслуживание сохраняют существующий lifetime; адаптеры хранилищ и новые команды не добавлены.

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

`tools/smoke_garage_snapshot_read_composition.py` проверяет инъекцию reader Garage, актуальность путей, каноническую сборку и композицию, context/runtime payload, порядок ошибок, изоляцию запросов и MCP композицию после ingress guards. Поддерживает сохранённые исходные методы через `--baseline` и ограничивает временные fixtures через `--scratch-root`.

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
