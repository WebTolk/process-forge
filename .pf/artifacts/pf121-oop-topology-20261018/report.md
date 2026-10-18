Исследование архитектуры ProcessForge после 1.2.0. Дата: 2026-10-18. Роль: `topology-worker`. Статус: исследование завершено; продуктовая реализация и повторная приёмка ранее выполненных срезов не заявляются.

Идентичность подготовленного задания:

```text
project_id: process-forge
run_id: garage-pf121-oop-topology-20261018-current-architecture-documents-admitt
assignment_id: pf121-oop-topology-20261018-current-architecture-documents-admitted-oop
context_id: pf121-oop-topology-20261018-current-architecture-documents-admitted-oop-capsule
attempt: 1
```

Фактическая база — текущие исходники с `VERSION = 1.2.0`, HEAD `2f027b9ff56019b96e17280dfe7e50bc7f5a43bc`. Проверка отслеживаемых изменений в `src/`, `tools/`, `docs/`, `runtime/` не показала изменений относительно HEAD. Это не утверждение о чистоте всего рабочего дерева.

Serena и IDE MCP среди доступных инструментов отсутствуют. Использованы ограниченный `rg`, чтение файлов и AST без импорта продуктовых модулей. Архивные Python-копии из артефактов, dogfooding и временных распаковок не использовались как текущий код. Продукт, существующие документы и файл отчёта не записывались; Work, инфраструктура и вложенные агенты не запускались.

**Архитектурные источники и их актуальность**

| Источник | Оценка и применение |
|---|---|
| `.pf/artifacts/original-architecture-alignment-20261010/migration-contract.md` | Действующий контракт переноса: реализация принадлежит Core; принятый срез исключает прямой и косвенный возврат в монолит; потребители переводятся вместе с владельцем. |
| `.pf/artifacts/progressive-oop-boundary-20261010/decision.md`, `boundary.md` | Зафиксированное пользовательское направление: небольшие законченные срезы по разным существующим областям. Пять read foundation срезов не исчерпывают OOP-01. |
| `.pf/artifacts/oop-refactor-clarification-20261005/clarification.md` | Актуальная рамка: рефакторинг существующего PF, сохранение поведения, повторное использование владельцев; Kernel/DI/plugin engine не обязательны. |
| `.pf/artifacts/pf-core-domain-map-20261005/domain-map.md`, `refactoring-plan.md` | Полезная карта 15 областей. Некоторые пути и предписания сохранения старых адаптеров уже исторические; их уточняет контракт от 10 октября. |
| `.pf/artifacts/pf-framework-architecture-20261005/adr.md`, `domain.md`, `direction.md` | Логические слои и инварианты полезны. Документы имеют статус предложения; точные Kernel/Application/container/lifetime механизмы нельзя считать реализованными или обязательными только по этому пакету. |
| `.pf/artifacts/python-framework-20261005/program.md`, `oop-01.md`…`oop-05.md` | Спецификации открытых эпиков. Формулировка исходной программы «реализация не начата» описывает момент постановки, а не текущий код. |
| `.pf/artifacts/python-architecture-20261005/architecture.md` | История первого узкого read-port решения. `CurrentWorkService` и его зависимости с тех пор существенно изменились. |
| `.pf/artifacts/python-core-refactor-phase-a-20260814/python-core-target-architecture.md`, `architecture-reconciliation.md`, `final-architecture-review.md` | Исторические варианты и gates. Направление modular Core + thin adapters сохраняет смысл; старые очередность, пути и характеристика MCP как read-only не описывают текущую поставку. |
| `docs/concepts/python-core-structure.md`, русская версия | Наиболее подробная текущая карта исходников и оставшихся callback-связей. Требует точечных уточнений о кэше и актуальных сигнатурах. |
| `src/processforge_core/AGENTS.md`, `tools/pf_cli/AGENTS.md` | Действующие правила размещения: неглубокие пакеты по ответственности, явные зависимости, сохранение внешнего контракта, отсутствие новых внутренних compatibility aliases. |
| `docs/concepts/document-reads.md`, `runtime-model.md`, `runtime-mcp.md`, `runtime-configuration.md`, `file-first-processes.md`, `known-limitations.md`, `requirements.md` | Текущие эксплуатационные границы: файловый режим, ограниченное повторное использование YAML-разбора, необязательный app-server, отдельный MCP lifecycle, локальный SQLite. |
| `docs/concepts/work-execution-contract.md`, `prepared-input.md`, `work-resources.md`, `work-continuation.md` | Контракты identity, immutable inputs, актуального доступа, material verification и attempts. Срезы ООП должны сохранять эти границы. |
| `.pf/adr/0001-processforge-product-boundary.md`, `0002-workplace-and-project-layer.md`, `file-flow-canonical-contract.md`, `agent-session-atomic-unit.md`, `director-ledger-inspector-boundary.md`, `config-driven-behavior-contract.md` | Устойчивые продуктовые решения. Описание первоначального MVP следует отличать от сегодняшнего устройства хранения. |
| `docs/audits/pf-audit-followups-20261014.md`, `CHANGELOG.md`, `docs/releases/1.2.0.md` | Согласованно оставляют OOP-01…OOP-05 открытыми. Релизные заметки не заменяют доказательства текущей установленной или подключённой среды. |
| `docs/releases/dev-oop-context-metadata-20261015.md`, `dev-oop-capability-records-20261015.md` | Историческая квалификация конкретных metadata/capability срезов на указанных в документах исходниках. Не общая приёмка нынешнего Core. |

Предоставленные inline-знания Python использованы как разрешённый вход. Внешние зеркала и документация самостоятельно не открывались.

**Фактическая структура исходников**

AST-разбор текущих продуктовых областей дал следующие размеры. Классы включают Protocol, ошибки и значения; это инвентаризация, не процент готовности ООП.

| Область | Python-файлы | Строки | Объявления классов |
|---|---:|---:|---:|
| `tools/processforge.py` | 1 | 25 362 | 8 |
| `src/processforge_core/` | 149 | 18 915 | 200 |
| `src/processforge_platforms/` | 4 | 132 | 4 |
| `tools/pf_cli/` | 35 | 3 800 | 54 |
| `tools/pf_runtime/` | 17 | 6 472 | 20 |

В монолите 990 объявлений функций верхнего уровня, включая повторные определения имён. Контрольный SHA-256 `tools/processforge.py`:

```text
e99d35af720db9e0d9a1c2c2e5736d7f93004aea98bf25e34edeb5a49cd14855
```

Топология уже включает общие Core-фабрики и самостоятельных владельцев. Однако нормальная сборка приложения продолжает загружать legacy-модуль: `RuntimeBootstrap` в `bootstrap.py` хранит `core: ModuleType`, а `bootstrap_runtime` использует `_load_legacy_core`.

CLI имеет отдельный `CliApplication`, parser registrars и часть command adapters. MCP и Host используют общие фабрики Core, одновременно сохраняя транспортные guards и legacy-зависимости. Наличие общей фабрики ещё не означает автономность собираемого сценария.

| Область | Фактические владельцы | Граница завершённости |
|---|---|---|
| Документы и примитивы | `documents.reader.YamlDocumentReader`, `documents.answers.AnswersDocumentReader`, `common.digests.FileDigestReader`, `common.ndjson.NdjsonReader`, `common.ids`, `common.paths` | Конкретные владельцы без необходимости передавать весь монолит. Строгий answers reader сохраняет собственные отказы. |
| Work discovery и записи | `work.inventory.WorkInventory`, `work.records.YamlWorkRecordReader`, `CurrentWorkService`, `work.metadata.WorkMetadataReadPass`, `WorkProjectionPolicy` | Самостоятельное чтение и проекции. Metadata pass принадлежит операции; он не является общей транзакцией файлов. |
| Контракт и чтение капсулы | `work.context_documents.ContextContractInputs`, `work.context_read.WorkContextReadService`, правила в `work.context` | Read path использует конкретные Core-входы. Создание полного контекста в `build_context_fields` ещё принимает legacy Core. |
| Каталог процессов | `ProcessCatalogReadService`, `OfficialProcessPackReader`, `ProcessDefinitionReadService`, `ProcessSummaryReadService`, модели и алгоритмы `process_catalog.service` | Конкретные default readers существуют. `ProcessSelectionService` и `ProcessPinReadService` выделены, но окружающие lifecycle-сценарии ещё имеют legacy-связи. |
| Проектный контекст | `ProjectMetadataReader`, `ProjectSnapshotReadService`, `ProjectSnapshotSourcesReader`, `ProjectContextSourcesReader`, `CapabilityRegistryReader` | Чтение metadata/snapshot/sources принадлежит Core. Полная сборка и freshness orchestration остаются в монолите. |
| Чистые проектные правила | `ProjectContextReadinessPolicy`, `ProjectContextPolicy`, `ProjectContextRules`, `ProjectSnapshotResolvedComparison`, `ResourceSnapshotRules`, `KnowledgeResourceSelector`, `ProjectContextSnapshotRenderer` | Реальные владельцы алгоритмов, пригодные для повторного использования. Они не завершают весь сценарий контекста. |
| Поиск и разрешение ресурсов | `ResourceResolveService`, `ResourceResolveReadService`, `WorkspacePathReferenceReader`, `WorkplaceSearchCatalogReader`, `ResourceSearchIndex`, `ResourceVersionPolicy` | Resolve имеет конкретный default read owner. Search сохраняет `LegacyResourceSearchReadAdapter` и зависимость от legacy freshness checker. |
| Work/prepared resources | `WorkResourceService`, `WorkResourceContextReadService`, `WorkMaterialReadService`, `ResourceDeclarationPolicy`, `ResourceBindingBuilder`; `PreparedResourceSnapshotReader`, `PreparedResourceSelectionPolicy`, `PreparedRegistryResourceReader`, `PreparedKnowledgeResourceReader` | Алгоритмы разделены; материал, budgets и admission имеют явных владельцев. Полные Work/prepared сценарии ещё используют legacy-операции. |
| Lifecycle, evidence и completion | `ProcessExecutionService`, `WorkStatePolicy`, `WorkSelectionService`, `EvidenceCollectionPolicy`, `EvidenceValidationService`, `StageReadinessPolicy`, completion services | Значительная декомпозиция существует. Координатор и ряд нормальных bindings возвращаются к legacy storage, clock, events и formatting. |
| Continuation и публикация | `ContinuationService`, отдельные read/status/contract/publication/cancellation services; `WorkDocumentPublisher`, `WorkEventPublisher`, `AssignmentCapsulePublisher`, `WorkTransitionCommitService` | Владение алгоритмами выделено. Полная независимость сценариев не достигнута: сохраняются deferred providers и legacy locks/events. |
| Конфигурация и диагностика | `ConfigService`, `YamlConfigStore`, `ConfigurationResolver`, frozen config values; `Logger`, `NullLogger`, `Sanitizer`, `JsonlSink` | Готовые владельцы следует переиспользовать. Конфигурационный resolver имеет отдельный контракт кэширования и last-valid поведения. |
| Presence и providers | `agents.presence.AgentPresenceReader`; `AdapterRegistry`, `AdapterPolicy`, `CodexHooksPolicy`, `CodexWorkerPolicy`, `RawIngressKernel` | Presence reader не владеет всей attendance lifecycle. Trusted provider policy уже существует отдельно от декларативных packs и capabilities. |
| Журналы и платформы | `ProcessEventJournal`, `RawHookJournal`, `sqlite_storage`; `FileSecurity`, Windows/POSIX реализации | Конкретное хранение и платформенные адаптеры уже выделены. Это не основание переносить текущие журналы по старому NDJSON-дизайну. |
| Egress и обслуживание | `egress.engine.Session`, `Store`, `JsonTransport`; модули `maintenance.update`, `maintenance.temporary_files`, `runtime.metrics` | Есть связные классовые и функциональные владельцы. Наличие функций внутри owning module само по себе не дефект ООП. |
| Интерфейсы | `CliApplication`, command adapters, parser registrars; `ActionCatalog`, `NativeActionGateway`, `ActionToolService`, `RuntimeProcess` | Частичная миграция интерфейсов выполнена. Host/service/MCP остаются также сборщиками и владельцами операционных обязанностей. |

По контракту от 10 октября следует различать выделенный алгоритм и полностью перенесённый сценарий. Например:

- `ProjectContextService` действительно не имеет поля Core, но `composition.py:361` связывает его `context_check` с `core.project_context_check_result`.
- `LegacyResourceSearchReadAdapter.context_checker` возвращает checker монолита.
- `ProcessExecutionService` хранит `core: Any`; его фабрики и операции используют legacy locks, события, форматирование, scope checks и другие функции.
- `work.context.build_context_fields` вызывает `core.merge_parameter_maps`.
- `prepared/input.py`, `prepared/resources.py`, `project/initialization.py`, `work/continuation.py`, `egress/service.py` сохраняют явные Core-зависимости.

Эти связи являются остатком миграции. Само отсутствие `core` в отдельном классе не позволяет объявить весь соответствующий use case автономным.

**Оставшиеся обязанности монолита**

| Ответственность | Текущие файлы и символы |
|---|---|
| Сборка project/workplace | `tools/processforge.py::build_project_files` — 726 строк; `build_workplace_files` — 321 строка. `project.initialization` ещё делегирует legacy-операциям. |
| Классификация и подключение контекста | `project_classifier_registry_documents`, `project_classifier_paths`, `classify_project`, `resolve_platform_contracts`, `resolve_specialization_context`. |
| Параметры и provenance | `merge_parameter_maps`, `merge_parameter_value`, `resolve_project_parameters`, `resolve_assignment_parameters`, `add_parameter_source`. |
| Полный snapshot/freshness | `_project_context_check_result` — 87 строк; `build_project_context_snapshot` — 385 строк; `write_project_context_snapshot_outputs`. Уже выделенные policies/readers используются внутри этих сценариев. |
| Authoring и contract validation | `process_from_authoring_answers`, `build_process_create_plan`, `validate_process_authoring_logic`, `validate_process_contract`, platform/knowledge authoring plans и транзакционная обвязка. |
| Attendance, leases и handoffs | `command_agent_checkin/heartbeat/checkout`, `update_stale_agent_presence`, lease commands, `command_handoff_*`, Director/orchestrator operations. |
| Worker execution и supervision | `prepare_worker_run`, `_collect_worker_run_locked`, worker commands, `supervisor_tick_result`, driver resolution/validation. |
| Общая инфраструктурная обвязка | `registry_file_lock`, JSON/YAML helpers, event/hook dispatch, часть runtime/bootstrap composition. |
| Поставка | Release, manifests, archive verification и update commands. Эта область требует сопоставления с отдельным исследованием установки/обновления. |
| CLI composition | `build_parser` — 475 строк. Registrars вынесены, но explicit wiring и многие handlers остаются здесь. |

Полный перенос freshness сейчас нельзя честно заменить классом, который через callback продолжит вызывать `build_project_context_snapshot` монолита. Аналогично перенос файла или переименование Core-зависимости в Protocol не завершает функциональный срез.

**Конкретные расхождения документов с кодом**

| Расхождение | Доказательство и следствие |
|---|---|
| Неуточнённое описание отсутствия общего document cache | `python-core-structure.md:116` говорит `no shared mutable document cache`. Между тем `common/request_scope.py` создаёт общий `_PARSE_CACHE = YamlParseCache()`. `document-reads.md` уже правильно описывает межзапросный content-keyed LRU и независимые копии результатов. Следует уточнить формулировку: общая retention разбора существует; общих выдаваемых mutable результатов и кэшированной authority нет. |
| Неполные сигнатуры фабрик в текущей карте | В `python-core-structure.md:148` у `build_current_work_service` не указан `work_metadata`. В описании `build_project_context_service` на строке 175 отсутствуют текущие `metadata` и `work_metadata`, присутствующие в `composition.py`. Это дрейф справочника внедрения зависимостей. |
| Старый план требует сохранять уже удалённые адаптеры | `pf-core-domain-map-20261005/refactoring-plan.md` предписывает сохранить `WorkReadCorePort` и `LegacyWorkReadAdapter`. В текущем `ports.py` их нет; `CurrentWorkService` расположен в `work/records.py`, фабрика использует конкретных владельцев. План следует читать как историю, с учётом более позднего migration contract. |
| Старые карты содержат прежние flat paths | В domain map встречаются `work_inventory.py`, `work_context.py`, `continuation.py`, `local_resource_search.py`, `core_update.py`. Текущие владельцы находятся в `work/`, `resources/`, `maintenance/` и других пакетах. Исторические approved документы не нужно переписывать; актуальную навигацию даёт текущая карта. |
| Историческое отсутствие database неоднозначно для нынешнего PF | ADR 0001 описывает продукт без обязательной database. Текущие `ProcessEventJournal`, `RawHookJournal` и `sqlite_storage` используют локальный SQLite, включая обязательные admission/verification данные. Современные requirements это отражают. Нужно различать отсутствие внешнего сервера БД и отсутствие встроенного SQLite. |
| Октябрьский journal design опирается на прежний алгоритм | `oop-presence-journal-20261012/report.md` описывает будущий перенос eager NDJSON read/append/fsync. Текущий `ProcessEventJournal` уже имеет SQLite admissions, indexes, verification state и pending dispatch. Такой дизайн нельзя исполнять без нового сопоставления с кодом. |
| Ранняя характеристика MCP как read-only устарела | Августовские architecture материалы описывают read-only facade. Текущий `mcp_server.py` обрабатывает `pf.work.start`, `pf.work.transition` и другие mutations; нынешний `runtime-mcp.md` это учитывает. |

Расхождения исторических планов не являются основанием возвращать старые адаптеры или алгоритмы. Текущие документы также правильно предупреждают, что OOP-01…OOP-05 остаются открытыми.

**Рекомендуемые следующие три небольших среза**

Предложения ниже относятся к будущим ограниченным implementation Work. Они не являются выполненными изменениями.

1. **Слияние параметров и provenance.**

   Текущие символы: `tools/processforge.py:8535` — `parameter_path`, `parameter_list_item_path`, `parameter_list_merges_by_id`, `merge_parameter_value`, `merge_parameter_maps`.

   Предлагаемый владелец — небольшой `ParameterMergePolicy` в `src/processforge_core/configuration/parameters.py`. Это одна связная обязанность рекурсивного merge; сбор источников, precedence слоёв и файловое чтение остаются у прежних сценариев.

   Затронутые consumers: `add_parameter_source` и `work/context.py::build_context_fields`. Они должны прямо использовать Core-владельца; callback к старому merge не допускается.

   Сохраняемый контракт:

   - `None` в этом алгоритме удаляет ключ. Его нельзя заменить null-as-inherit из runtime configuration.
   - Списки объединяются по `id` только при прежних условиях; сохраняются строковое сравнение ID, порядок, дубликаты и точные delete-маркеры.
   - Сохраняются deepcopy, изменение переданного provenance, пути записей и native errors.

   Зависимости — стандартная библиотека, без I/O и новой фабричной инфраструктуры. Проверки эквивалентности: существующие parameter cascade, assignment capsule и freshness smokes; направленное сравнение вложенных maps/lists, пустых значений, повторных ID, provenance и неизменности входов. Этот срез убирает конкретную обратную связь из Work compiler.

2. **Сопоставление правил классификаторов.**

   Текущие символы: `project_classifier_condition_matches`, `project_classifier_rule_matches` в `tools/processforge.py:3770`; общий `path_matches_pattern` на строке 3988.

   Предлагаемый владелец — `ProjectClassifierRulePolicy` в `src/processforge_core/project/classification.py`. Общий строковый matcher целесообразно разместить функцией в существующем `common/paths.py`: он также используется `detection_group_matches` и `platform_detection_matches`.

   Политика получает уже наблюдённое множество путей. Обход каталогов, исключения roots, загрузка registry/pack и activation остаются у прежних владельцев. Все consumers matcher переводятся вместе, без дублирования реализации.

   Сохраняемый контракт: приоритет ветки `all` перед `any`, false для пустых/неподходящих условий, short-circuit порядок, обработка `exists`, нормализация слешей, совпадение полного пути либо basename. Нужно сохранить именно текущее поведение `fnmatch.fnmatch`, включая платформенные особенности.

   Проверки: существующие data-driven classification, inventory pruning, official-pack и scan-boundary smokes; характеристические случаи смешанных `all`/`any`, неверных типов, basename и слешей. Срез делает правила доступными библиотечному потребителю без активации платформы или выдачи grants.

3. **Объявления и производство артефактов процесса.**

   Текущие символы: `artifact_definition_ids`, `declared_process_artifact_ids`, `produced_process_artifact_ids` в `tools/processforge.py:13964`.

   Предлагаемый владелец — `ProcessArtifactDeclarationPolicy` в `src/processforge_core/process_catalog/artifacts.py`. Он вычисляет существующие множества определённых, объявленных и производимых artifact IDs. Полный `validate_process_contract`, route reads и проверки companion/template files в этот срез не входят.

   Consumers: `validate_process_authoring_logic`, `validate_process_contract`, `builtin_process_catalog_report`. Они используют одного Core-владельца; сообщения проверок и их порядок остаются в прежних местах.

   Существенная ловушка: в монолите два определения `as_list`. Действующее позднее определение на строке 12713 возвращает `[]` для scalar, тогда как `process_catalog.service._as_list` оборачивает scalar в список. Механическое переиспользование последнего изменит обработку некорректных документов.

   Проверки: mapping/list формы деклараций, scalar и malformed значения, дубликаты, преобразования ID, строковые `produced_artifacts`, отсутствие мутации. Использовать существующие builtin catalog, authoring materialization и stage-contract checks. Этот владелец полезен и файловому authoring, и будущему редактору процессов.

Все три предложения выделяют группы правил с общей ответственностью. Они не создают класс для каждой функции и не требуют контейнера.

**Владение файлами и интеграция**

Честной параллельной выдачи этих срезов разным writers целиком нет: каждый затрагивает `tools/processforge.py`.

| Ответственность | Отдельное владение | Общая интеграция |
|---|---|---|
| Срез 1 | `configuration/parameters.py`, относящиеся к merge проверки | Монолит и `work/context.py` |
| Срез 2 | `project/classification.py`, `common/paths.py`, classification проверки | Монолит |
| Срез 3 | `process_catalog/artifacts.py`, artifact declaration проверки | Монолит |
| Интегратор | `tools/processforge.py`, затронутая общая документация и checksum inventory | Один writer, последовательные handoffs |

Предпочтительны три последовательные Work, каждая с полным переводом своих consumers и assurance до следующей. При разделении авторства новые модули могут иметь непересекающихся владельцев, но общий файл остаётся у одного интегратора. Разные диапазоны строк одного файла не дают непересекающихся file scopes.

Для каждого среза необходимы normal default composition без монолита, сравнение значений/ошибок/порядка, проверка всех найденных callers и изолированный импорт скопированного Core. После завершённой реализации — независимое ревью. Архив, установка, Runtime и actual connected host остаются отдельными границами доказательства.

**Соответствие продуктовой цели и открытые вопросы**

Текущие project-bound readers, явные project/workplace roots, immutable capsules и общие фабрики подходят файловому режиму и будущему управлению несколькими проектами. Операционные данные и grants должны проверяться в пределах конкретного вызова; выбранный проект нельзя удерживать как скрытый global current project.

Будущее управление несколькими устройствами пока не реализовано. Локальный app-server, SQLite journals и поддержка нескольких проектов не доказывают наличие распределённого scheduler, удалённой authority или web management. Для этого не требуется заранее вводить HTTP-типы в доменные правила или новый универсальный plugin loader.

Основному агенту остаётся сопоставить эти предложения с отчётами по библиотекам, установке и MCP. В частности:

- выбрать ближайшую ротацию областей, учитывая большой остаток Ledger, handoff, workers и maintenance;
- закрепить актуальный migration contract и относящиеся specs в новых implementation inputs;
- уточнить текущий справочник кэша и фабрик, сохранив исторические approved материалы;
- отдельно определить дальнейшую границу полного snapshot/freshness сценария без обратных callbacks в монолит.

Блокирующего недостатка входов для этого исследования не обнаружено. Полнота динамических consumers и поведенческая эквивалентность будущих изменений остаются предметом implementation assurance.

Журнал выполнения: `2026-10-18`, `topology-worker` — проанализированы архитектурные источники, текущие `src/`, CLI/Runtime adapters и относящиеся существующие проверки; выполнен AST-разбор 206 продуктовых Python-файлов в перечисленных областях. Функциональные и полные релизные наборы не запускались. Записей и продуктовых изменений нет. Ограничение инструментария — отсутствие Serena/IDE MCP; выводы основаны на статическом анализе и не заявляют runtime, installed или connected-host acceptance.