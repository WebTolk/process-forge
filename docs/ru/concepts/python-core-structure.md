# Структура Python-Ядра

Это справка по реализации для разработчиков Core. Для обычной работы начните
с [Garage Core](garage-core.md), [модели Runtime](runtime-model.md) и общих
[требований](../requirements.md). Описания владельцев и переноса кода ниже
не добавляют шагов к пользовательскому сценарию.

Карта действий принадлежит `processforge_core.operations.catalogue`.
`ActionCatalog` получает данные описаний и необязательные факты явно выбранной
Work. Он не импортирует argparse, Runtime и CLI-монолит, не вызывает обработчики
и не выдаёт полномочия. Чтение регистраций CLI/MCP относится к адаптеру
`tools/pf_runtime/action_catalog.py`. Нативное исполнение MCP использует прежних
владельцев и не означает завершённый перенос legacy-воркеров в ООП.
См. [карту действий](action-discovery.md).

Ядро развивается поэтапно. `tools/processforge.py` остаётся действующим legacy facade, а не удалённым кодом. CLI, MCP, hooks и aliases bootstrap сохраняются.

Цель миграции — тонкий фасад совместимости: точки входа разбирают и оформляют транспортные данные, затем вызывают ООП-ядро, которому принадлежат поведение, состояние и правила. Каждая перенесённая обязанность использует конкретных владельцев Core без импорта или вызова монолита. Оставшиеся обратные вызовы учитываются как незавершённый перенос.

**pf-app-server** — необязательный долгоживущий фоновый процесс-приложение/сервер ProcessForge, запускаемый существующими командами runtime/server. Он обслуживает Runtime-планировщик и общие прикладные службы; CLI и MCP являются отдельными входными адаптерами. Термин обозначает работающий процесс и срок его жизни; названия команд, API и конфигурации сохраняют совместимость.

## Размещение По Пакетам

Новые модули реализации размещаются в пакетах по ответственности согласно
[правилу ядра](../../../src/processforge_core/AGENTS.md). Имена пакетов — короткие
и в нижнем регистре, модулей — `snake_case.py`, классов — `CapWords`. Модуль может
содержать службу, её исключения и связанные вспомогательные функции; обязательного
соответствия «один класс — один файл» нет. Дерево пакетов должно быть неглубоким,
а `__init__.py` — минимальным.

Существующие Work-модули перенесены в `processforge_core.work`: `context`,
`context_read`, `inventory`, `records`, `metadata`, `resources`, `resource_material`,
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
| `src/processforge_core/project/file_templates.py`, `project/runtime_launchers.py` | Прежние файлы проекта и байты шаблонов запуска с явным корнем дистрибутива и конкретными входными службами инициализации и обнаружения. |
| `src/processforge_core/project/workplace_templates.py`, `project/workplace_terms.py`, `process_catalog/profile_packs.py` | Прежние файлы рабочего места, термины и выбор официальных пакетов по профилю. |
| `src/processforge_core/project/initialization_discovery.py` | Прежняя сборка классификации и обнаружения, подбор общих ресурсов и чтение текста реестров; инициализация получает явную операцию генерации файлов. |
| `src/processforge_core/project/configuration_inputs.py` | Прежнее разрешение конфигурации проекта и устройства с тем же общим resolver и сохранением последней корректной конфигурации. |
| `src/processforge_core/agents/process_events.py`, `agents/hook_dispatch.py` | Прежние допуск событий, запись журнала, диагностика и выполнение hooks через конкретные зависимости Core; сборка Work явно передаёт необязательный recorder. |
| `src/processforge_core/chat/writer.py` | Прежние добавление сообщений, блокировки, обработка повторов, запись событий и синхронизация экспорта. |
| `src/processforge_core/maintenance/release_manifest.py`, `maintenance/release_plan.py`, `maintenance/release_commands.py` | Прежние правила манифеста выпуска, упорядоченные планы команд и их записи; выполнение остаётся у текущего адаптера. |
| `src/processforge_core/common/markdown.py`, `common/release_identity.py` | Общие прежние форматирование Markdown-списков и имя, версия и шаблон хеша выпуска. |
| `src/processforge_core/resources/project_packages.py` | Манифесты пакетов проекта, записи корней, актуальные candidates/index, дубликаты и зависимости через конкретные пути и документы Core. |
| `src/processforge_core/project/platform_resolution.py` | Прежнее рекурсивное разрешение иерархии платформ и сбор ресурсов/зависимостей через конкретные каталоги и правила Core. |
| `src/processforge_core/process_catalog/semantics.py` | Прежняя полнота авторинга, проекции семантики и упорядоченное сравнение совместимости. |
| `src/processforge_core/presentation/process_parity.py` | Прежние Markdown-отчёты импорта и паритета процесса отдельно от семантических правил. |
| `src/processforge_core/runtime/worker_plans.py` | Прежние начальные планы работников, правила подагентов и зависимостей, рекурсия и актуальное чтение завершённости назначений. |
| `src/processforge_core/project/platform_selection.py` | Прежний выбор платформ/типов/реестров и находки через конкретных владельцев ответов, документов, обнаружения, платформ и пакетов. |
| `src/processforge_core/maintenance/registries.py` | Прежнее чтение entity/override/installed реестров и разрешение пути установки; без установки и записи версий. |
| `src/processforge_core/runtime/worker_validation.py` | Прежние проверки планов, дополнительных ключей и отчётов подагентов. |
| `src/processforge_core/project/hooks.py` | Путь конфигурации hooks и прежний порядок проверок. |
| `src/processforge_core/common/record_validation.py` | Прежняя проверка полей event/chat и секретов. |
| `src/processforge_core/process_catalog/routes.py` | Текущий поиск маршрута, проверка и требуемая роль. |
| `src/processforge_core/process_catalog/handoffs.py` | Каталог, путь и мягкое чтение handoff. |
| `src/processforge_core/maintenance/validation.py` | Прежние проверки overrides и нормализованного манифеста обновлений. |
| `src/processforge_core/project/platform_documents.py` | Прежнее построение модели и байтов документов платформы. |
| `src/processforge_core/project/registry_checks.py` | Текущая проверка путей реестров и корней пакетов. |
| `src/processforge_core/common/text.py` | Прежние завершающая строка и оформление подсказок. |
| `src/processforge_core/common/yaml_dump.py` | Точная прежняя сериализация скаляров и рекурсивного YAML. |
| `src/processforge_core/process_catalog/audit.py` | Прежний отчёт каталога процессов и плоский индекс пакетов. |
| `src/processforge_core/project/setup.py` | Прежние модель предложения настройки workplace и Markdown. |
| `src/processforge_core/project/registry_write.py` | Прежнее обновление реестра с проверкой схем и атомарным staging. |
| `src/processforge_core/project/templates.py` | Прежний выбор корня шаблонов и поиск манифестов. |
| `src/processforge_core/project/platform_validation.py` | Прежняя упорядоченная семантическая проверка платформ. |
| `src/processforge_core/common/policies.py` | Общие функции policy entries и сопоставления ID. |
| `src/processforge_core/project/requirements.py` | Прежняя проверка зависимостей платформ и чтение ID реестров. |
| `src/processforge_core/resources/records.py` | Прежние defaults, публичные ссылки и нормализация ресурсов. |
| `src/processforge_core/resources/package_checks.py` | Прежняя упорядоченная диагностика пакетов знаний. |
| `src/processforge_core/resources/index_checks.py` | Прежние проверки индексов, path_ref и ресурсов проекта. |
| `src/processforge_core/work/worker_assignment.py` | Строгое чтение Assignment и прежний текст worker launch prompt. |
| `src/processforge_core/authoring/plans.py` | Прежние модели авторинга и stdout плана. |
| `src/processforge_core/authoring/inputs.py` | Прежние режимы, пути, журналы и guards авторинга. |
| `src/processforge_core/process_catalog/examples.py` | Прежние байты документов примера авторинга процессов. |
| `src/processforge_core/common/status.py` | Общая прежняя проекция итогового статуса. |
| `src/processforge_core/maintenance/candidate_read.py` | Прежнее свежее чтение и поиск JSON кандидатов. |
| `src/processforge_core/project/session_read.py` | Прежние статусы отчётов, недавние файлы и legacy freshness. |
| `src/processforge_core/configuration/specializations.py` | Прежние registry/path candidates и индекс специализаций. |
| `src/processforge_core/evolution/validation.py` | Прежние упорядоченные проверки кандидата знаний и категории. |
| `src/processforge_core/maintenance/transfer.py` | Прежнее получение update manifest и перенос артефакта. |
| `src/processforge_core/authoring/journals.py` | Прежняя запись журнала авторинга и точные ошибки очистки. |
| `src/processforge_core/configuration/parameter_sources.py` | Прежние provenance, пути, чтение и merge источников параметров. |
| `src/processforge_core/project/report_read.py` | Прежние Markdown sections, справка и проекция resource report. |
| `src/processforge_core/project/initialization_inputs.py` | Прежние исходные типы, режим и defaults проекта. |
| `src/processforge_core/process_catalog/contracts.py` | Прежняя упорядоченная проверка контракта процесса, чтение route-документов и общие режимы handoff. |
| `src/processforge_core/agent_entry/` | Контракт входа, профили, клиентские адаптеры, стартовая подсказка, защищённое размещение инструкций и восстановление. |
| `src/processforge_core/completion/` | Правила завершения Run, итоговые документы и индекс задач, подготовка, чтение, проверка и восстановление по записи о завершении. |
| `src/processforge_core/evidence/` | Прежние правила сбора и identity доказательств, нормализация и актуальная диагностика файлов, удовлетворение требований и gates, порядок blockers готовности через явные зависимости. |
| `src/processforge_core/garage.py` | Оставшиеся legacy helpers; текущие Work readers находятся в `work/records.py`, контекст проекта и reconciliation — в `project/`. |
| `src/processforge_core/work/projection.py` | Прежние чистые правила проекций и классификации Work, без Core и полномочий lifecycle. |
| `src/processforge_core/work/metadata.py` | Явный проход чтения метаданных Run/Assignment для сводки и каталога; повторное использование разбора текущего содержимого и полные актуальные входы проверки журнала завершения. |
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
| `src/processforge_core/process_catalog/summary.py` | Описание разрешённых процессов с конкретным каталогом по умолчанию и необязательным узким портом каталога для внедрения, без обратного вызова монолита. |
| `src/processforge_core/work/publication.py` | Прежняя атомарная публикация текста/YAML через отложенные зависимости форматирования и записи. |
| `src/processforge_core/work/events.py` | Прежняя структура события Work и последующая диагностика через типизированный динамический emitter. |
| `src/processforge_core/work/capsule_publication.py` | Прежняя неизменяемая публикация capsule с отложенными зависимостями и сохранённым exclusive open. |
| `src/processforge_core/process_execution.py`, `work/continuation.py` | Управляемый lifecycle, выбор работы, pinned execution, evidence, завершение и восстановление. |
| `src/processforge_core/completion/request.py` | Прежняя проверка готовности и обработка запроса завершения с живыми callbacks фасада. |
| `src/processforge_core/work/state.py` | Чистые правила completion/action/blockers и прежняя проекция ответа состояния Work, без ввода-вывода и полномочий на переход. |
| `src/processforge_core/work/automation_readiness.py`, `work/transition_rejection.py` | Прежние проекции готовности автоматизации, чтение актуальных событий Assignment и правила ответа при восстанавливаемом отказе перехода через явные зависимости. |
| `src/processforge_core/work/record_catalog.py` | Прежний проверяемый каталог активных и исторических Run/Assignment с учётом незавершённого completion и явными актуальными зависимостями. |
| `src/processforge_core/documents/reader.py`, `work/inventory.py` | Чтение YAML и актуальный отсортированный обход без общего изменяемого кеша документов. |
| `src/processforge_core/work/records.py` | Чтение актуальных Run/Assignment; выбор работы и восстановление остаются в прикладном сервисе. |
| `src/processforge_core/work/context_read.py` | Актуальная проверка капсулы и нормализация Assignment через конкретные зависимости Core. |
| `src/processforge_core/work/context_documents.py` | Конкретные поля и документы Work, проекции путей/scopes/dependencies, наблюдение required sources и проекция coordination капсулы. |
| `src/processforge_core/work/context.py` | Прежняя компиляция контекста Assignment; слияние параметров вызывает ParameterMergePolicy напрямую, остальные legacy-зависимости компилятора сохраняются. |
| `src/processforge_core/process_catalog/` | Конкретные читатели каталога и effective ProcessDefinition; выбор из предложенных процессов и подготовка pin сохраняют явные зависимости операций. |
| `src/processforge_core/project/metadata.py` | Живое чтение ID проекта, manifest и корня .pf через Core YAML; общий владелец для контекста, каталога и ресурсов. |
| `src/processforge_core/project/snapshot.py` | Чтение актуального ProjectContextSnapshot через конкретные читатели YAML и файловых хешей Core, привязанные к корню проекта. |
| `src/processforge_core/common/digests.py` | Прежнее чтение SHA256 исходных байтов файла, общее для snapshot, фасадов монолита и maintenance update. |
| `src/processforge_core/configuration/parameters.py` | ParameterMergePolicy без состояния: прежнее слияние карт параметров и упорядоченный provenance без зависимости от монолита. |
| `src/processforge_core/project/classification.py` | ProjectClassifierRulePolicy без состояния для проверки прежних правил классификации; реестры, обход и активация сохраняют legacy-владельцев. |
| `src/processforge_core/common/paths.py` | Общий примитив path_matches_pattern для классификации и обнаружения вместе с неизменённым helper rel. |
| `src/processforge_core/process_catalog/artifacts.py` | ProcessArtifactDeclarationPolicy без состояния для defined, declared и produced ID артефактов; полные валидаторы и I/O companion-файлов сохраняют legacy-владельцев. |
| `src/processforge_core/process_catalog/authoring.py` | ProcessAuthoringDefinitionBuilder: прежние значения по умолчанию, нормализация ответов и построение процесса с конкретными правилами evolve. |
| `src/processforge_core/process_catalog/evolution.py` | ProcessEvolutionPolicy: прежние значения evolve по умолчанию, нормализация и упорядоченные проверки. |
| `src/processforge_core/runtime/drivers.py` | RuntimeDriverDefinitionPolicy: прежние встроенные документы, реестр, placeholders, limits и проверки готовности документа. |
| `src/processforge_core/maintenance/sites.py` | UpdateSitePolicy: прежние идентификаторы источников, записи сайтов, переопределения и слияние политик без I/O. |
| `src/processforge_core/process_catalog/presentation.py`, `process_catalog/coordination.py` | Прежнее оформление authoring-текстов и общая проекция требований координации процесса. |
| `src/processforge_core/runtime/catalog.py` | RuntimeDriverCatalogReader: актуальное чтение реестров и документов с явным корнем дистрибутива и конкретными читателями Core. |
| `src/processforge_core/evolution/candidates.py` | KnowledgeCandidateTargetingPolicy: прежние идентификаторы, target/routing, готовность promotion и проверка targeting. |
| `src/processforge_core/maintenance/versions.py`, `maintenance/presentation.py` | Прежняя нормализация и выбор версий обновления, оформление assessment. |
| `src/processforge_core/project/coordination.py` | ProjectCoordinationReader: прежние defaults, нормализация режимов и актуальное чтение project/workplace coordination. |
| `src/processforge_core/common/privacy.py`, `evolution/privacy.py` | Общие канонические текстовые шаблоны/предикаты и прежние evolve findings, redaction и рекурсивное преобразование значений. |
| `src/processforge_core/maintenance/source_contracts.py` | UpdateSourceContractPolicy: прежние trust/URL/env/source проверки, валидация реестра и стабильная сортировка. |
| `src/processforge_core/work/outputs.py` | WorkOutputPolicy: прежние пути выходов/отчётов, waiver, проверки required outputs и verification fingerprint. |
| `src/processforge_core/project/detection.py` | ProjectDetectionService: актуальный общий список файлов и прежние правила обнаружения платформы. |
| `src/processforge_core/runtime/environment.py` | WorkerEnvironmentPolicy: placeholders, сохраняемое явное окружение и наследование только при запуске. |
| `src/processforge_core/maintenance/schema_checks.py` | UpdateSchemaChecks: существующее подмножество JSON Schema и актуальное чтение схем с явным корнем дистрибутива. |
| `src/processforge_core/work/paths.py` | WorkPaths: прежние пути Run, Assignment, артефактов, handoff и worker attempt с различной нормализацией ID. |
| `src/processforge_core/runtime/command.py` | WorkerCommandBuilder: прежняя проекция sandbox и сборка команды через конкретные политики Core. |
| `src/processforge_core/project/platforms.py` | PlatformContractReader: актуальный каталог seed/project/workplace с прежним перекрытием и fallback. |
| `src/processforge_core/maintenance/documents.py` | UpdateDocumentReader: прежние пути реестров, YAML/JSON, doctor checks и локальные file URL. |
| `src/processforge_core/runtime/selection.py` | RuntimeDriverSelectionService: прежний выбор драйвера задания и сохранённой команды через конкретные Core readers/policies. |
| `src/processforge_core/project/platform_policy.py` | PlatformContractPolicy: прежние проекции ссылок, зависимостей и required/recommended/optional ресурсов. |
| `src/processforge_core/process_catalog/validation.py` | ProcessAuthoringValidationService: прежние authoring logic, companion paths/checks и канонические workflow/iteration constants. |
| `src/processforge_core/common/json_io.py` | Каноническая прежняя json_read с актуальным чтением и исходными ошибками. |
| `src/processforge_core/common/checks.py`, `common/ids.py`, `common/values.py` | Общие изменяемый Check и фабрика, примитивы идентификаторов, заголовков, списков и исходных словарей параметров. |
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
| `src/processforge_core/composition.py` | Общие фабрики сервисов и оставшийся LegacyResourceSearchReadAdapter; перенесённые читатели текущей работы, контекста, определений процессов и разрешения ресурсов используют конкретных владельцев Core. |
| `src/processforge_core/bootstrap.py` | Существующая сборка runtime-модулей и ленивый доступ к фабрикам сервисов. |
| `tools/processforge.py`, `tools/pf_runtime/` | Legacy CLI facade, транспортные адаптеры, host и provider policies. |

`build_current_work_service(project_root, *, documents=None)` создаёт конкретный CurrentWorkService с читателями YAML и inventory из Core. RuntimeBootstrap, контекст и start вызывают этого владельца напрямую; LegacyWorkReadAdapter и WorkReadCorePort удалены. При сборке ввод-вывод не выполняется, общий кеш сервисов и DI-контейнер не вводятся. Оставшиеся обратные вызовы bootstrap/lifecycle требуют отдельных переносов.

`CurrentWorkService(project_root, documents=...)` получает читатель YAML, а не монолитный Core. Читатель по умолчанию, inventory и правила проекции принадлежат Core; текущие потребители используют конкретного владельца. Путь класса, порядок обхода, fallback отсутствующего assignment, исключение bootstrap placeholders, форма summary и обработка ошибок сохраняются.

`build_process_execution_service(project_root, workplace_root, core, *, observer=None, records=None, context=None, definitions=None, snapshots=None)` используется CLI, MCP и Host/Daemon. Метод `RuntimeBootstrap.process_execution_service(...)` вызывает ту же фабрику. Сборка не загружает CLI, не выбирает проект, не читает конфигурацию и не выполняет ввод-вывод. Прежний конструктор `ProcessExecutionService` с тремя аргументами сохранён; дополнительные зависимости передаются только по имени и не входят в equality/repr. Оставшиеся зависимости от legacy явные, без универсального интерфейса Core.

`WorkRecordReadPort` содержит `runs`, `load_run` и `load_assignment`. По умолчанию фабрика подключает `YamlWorkRecordReader` на существующих `WorkInventory` и YAML loader. Пути и документы читаются актуальными, общего кеша между запросами нет. Прямой старый конструктор сохраняет прежний обход и private path helpers, включая переопределения в подклассах. Читатель не выбирает Work, не скрывает дубликаты и aliases и не решает вопросы восстановления.

`WorkContextReadPort` остаётся точкой внедрения для чтения контекста работы.
По умолчанию `WorkContextReadService` получает только корень проекта и конкретный
`work.context_documents.ContextContractInputs`, которому принадлежит исходная логика
нормализации и чтения через Core YAML, IDs и пути. `LegacyWorkContextAdapter` и
обратные вызовы в старый Core удалены. Прежние функции монолита вызывают методы
Core. Общие правила `work.context` проверяют identity/intent, pins, scope и stage
views; сохранены проверки размера, пути, checksum, порядок отказов и актуальное
чтение файлов. Старый Core не передаётся в стандартный читатель. Общая сборка
контракта и проверки capability в режиме require-ready остаются отдельными
незавершёнными переносами; владение всем validation/bootstrap здесь не заявляется.

`ProcessDefinitionReadPort` предоставляет `effective_process(run)`. Конкретный `ProcessCatalogReadService(project_root)` читает контекст каталога проекта/рабочего места и активные пакеты через владельцев документов и путей Core, затем использует прежние алгоритмы каталога. `ProcessDefinitionReadService(project_root, *, catalog=None)` обращается к этому владельцу и существующей канонической функции fingerprint. Ленивой фабрике `build_process_definition_read_service(project_root)` и координатору больше не передаётся resolver монолита; `LegacyProcessDefinitionAdapter` удалён. Фасад контекста каталога в монолите вызывает владельца Core. Для валидных и повреждённых pin каталог не читается; определения без pin читаются заново при каждом вызове, копии сохраняют неизвестные поля. Статусы `pinned`, `corrupt`, `legacy_unpinned`, `missing`, границы исключений и полномочия lifecycle прежние.

`ProjectSnapshotReadPort` предоставляет `load(path=None)` и `checksum(path)` для явного внедрения читателя. Стандартный `ProjectSnapshotReadService` получает корень проекта и конкретные реализации Core: `YamlDocumentReader` и `FileDigestReader`. `LegacyProjectSnapshotAdapter` удалён; обе фабрики snapshot принимают только корень проекта. Обычные потребители — контекст проекта, process execution, Garage mode, отчёты, поиск и разрешение ресурсов, Work resources и prepared resources — читают snapshot без обратного вызова старого Core. Создание pin по-прежнему передаёт один захваченный путь загрузке и checksum; выбор ресурсов, preflight и capsule capture читают документ отдельно. Сохранены канонические пути, маркеры ошибок YAML, поведение отсутствующего файла, хеш исходных байтов и изоляция разбора внутри запроса. `FileDigestReader` также обслуживает оба фасада `sha256_file` монолита и фасад maintenance update. Проверки generation остаются в `work/context.py`; validator не получает новую зависимость чтения актуального снимка. Остальные адаптеры lifecycle, ресурсов и bootstrap требуют дальнейшего переноса.

`ProcessExecutionService.state()` сохраняет точный выбор Work, проверки контекста и pins, evidence/outcomes и готовность полномочий. `WorkStatePolicy` отдельно вычисляет требования завершения и action/blockers по переданным записям. Она не читает файлы, не меняет записи, не выбирает caller identity и не переводит процесс. Приоритеты конечного состояния, завершения, блокировки и незавершённости прежние; execution_readiness остаётся отдельным полем ответа.

`ProjectContextService` находится в `project/context.py` и не имеет поля Core. Два пути проекта/workplace и обязательные именованные зависимости snapshot/чтения описывают пять прежних операций. `build_project_context_service(project_root, workplace_root, core, *, snapshots=None)` сохраняет сигнатуру потребителей и собирает зависимости без I/O; стандартный reader создаётся только при `None`, поэтому ложный в логическом контексте переданный reader сохраняет identity. Пути, документы и ошибки читаются актуальными, checksum для этих операций не требуется. В начале каждого `context()` четыре фабрики mode/report/process-summary/boundary захватываются до freshness check в отдельный `ProjectContextReaders`; прочие helpers разрешаются в прежних местах использования. Сохранены `scoped_request`, всегда явный workplace, check перед snapshot и отказ от основного чтения при broken check. Mode/Reports используют независимые стандартные readers, а не порт контекста. Runtime resolver получается до вычисления `self.snapshot()`. Все ключи, resource values, порядок вызовов и изменение рекомендации continuation сохранены. MCP вызывает прежнюю фабрику после ingress guards. Старый Garage class/import alias, совместимость конструктора, кеш и новые полномочия не вводятся.

`ResourceSearchService` требует узкий `ResourceSearchReadPort` вместо общего объекта Core и сохраняет необязательное keyword-only внедрение `snapshots`. `LegacyResourceSearchReadAdapter` на границе composition выполняет прежние чтения Core и сохраняет позднее получение вызываемых функций. Явно переданный пустой snapshot исключает загрузку, а falsey внедрённый reader сохраняет свою identity. Freshness guard поиска предшествует чтению, а blocked readiness сохраняет существующее чтение для coverage. `build_resource_search_service` сохраняет опубликованную сигнатуру и собирает существующего MCP потребителя поиска без I/O после ingress guards. Проектный контекст сохраняет прежнюю заменяемую привязку сервиса и передаёт тот же read adapter. Index maintenance, аргументы запроса, navigation, coverage, payload и границы обработки ошибок сохраняют прежнее поведение.

`ResourceResolveService(project_root, workplace_root, reads=None, *, snapshots=None)` по умолчанию использует конкретный `ResourceResolveReadService`. ID проекта, живые снимки и переносимые ссылки на пути читаются через владельцев Core; `LegacyResourceResolveReadAdapter` удалён. Общая фабрика Host и MCP — `build_resource_resolve_service(project_root, workplace_root, *, snapshots=None)`. ID читается первым; пустой ID ресурса возвращает сведения о проекте без чтения снимка. Ложные в логическом контексте внедрённые читатели и снимки сохраняют identity; порядок вычисления resolver прежний. `WorkspacePathReferenceReader` владеет разрешением реестров, пакетов и констант путей; общие helpers поиска/Garage/Work вызывают его без объекта монолита. Selection, aliases, исходные поля, navigation, ошибки и порядок Host/MCP binding/freshness guards сохранены. Зависимости ResourceSearchService от контекста и Runtime требуют последующего переноса; независимость всей подсистемы ресурсов здесь не заявляется.

`GarageModeService` находится в `project/mode.py` и принимает `(project_root, workplace_root, *, snapshots)` с обязательным `ProjectSnapshotReadPort`, без Core. Зависимость исключена из repr/equality. Прежний fallback `snapshot or ...` сохранён: пустой snapshot вызывает `snapshots.load()`, непустой исключает чтение. `build_garage_mode_service(project_root, workplace_root, core, *, snapshots=None)` создаёт стандартный reader только при `None`, сохраняя falsey reader, и не выполняет I/O. Context не передаёт собственный порт в mode fallback. Координация, session, blockers и политика mode прежние; одной session недостаточно для Forge. Старый конструктор и module alias не сохраняются.

`DerivedReportLifecycleService` и `DERIVED_REPORTS` находятся в `project/reports.py`. Обязательные именованные зависимости `snapshots` и `flow_root` не содержат Core и не читают файлы при сборке. Фабрика создаёт независимый стандартный reader только для `None` и откладывает получение flow root до status. Context не передаёт свой reader. Пустой snapshot по-прежнему вызывает чтение перед flow root; порядок отчётов, пути, timestamps, проверки файлов, прежние исключения и итоговый status сохранены.

`ExecutionProjectReadService` находится в `project/context_read.py`. Обязательные именованные зависимости — пути проекта/workplace, resolver типизированной проверки контекста, resolver document loader и отложенный flow root. Каждая приватная `_context_check`/`_manifest` собирает сервис без I/O и кеша. Execution передаёт workplace явно только при наличии `workplace.yaml`; `ProjectContextService.check` всегда передаёт его явно. Loader получается до переопределяемого `_flow_root`, сохраняя порядок чтения и исключений. Приватные операции, проверки доступа и lifecycle authority остаются у координатора.

`ProcessSummaryReadService(project_root=None, catalog=None)` владеет описаниями разрешённых процессов и по умолчанию обращается к конкретному каталогу; для проверки доступен узкий порт его чтения. Сохранены выбор из snapshot/manifest, порядок и дубликаты кандидатов, текущий ID/stage count, fallbacks name/purpose/description и обработка только OSError/ValueError/SystemExit. Без корня проекта определения не читаются. `build_process_summary_read_service(project_root=None)` не выполняет ввод-вывод при сборке и не передаёт resolver монолита или общий Core. ProjectContextService вызывает её в прежнем месте построения ответа. Поле definition_resolver удалено; перенос проверяется на настоящих файлах и стандартном пути скопированного Core.

`FreshSessionBoundaryReadService` расположен рядом с WorkBoundaryAdvisoryService в work/boundary_advisory.py. Корень проекта, конкретный читатель документов Core и существующая реализация относительного пути обеспечивают чтение границы завершённой работы для новой сессии без адаптера монолита. `build_fresh_session_boundary_read_service(project_root)` собирает этого стандартного владельца. Governed Work возвращается до чтения. Сохранены glob order, совпадающие timestamps, последний пригодный completed handoff, актуальная проверка route, стабильная дедупликация процессов и запрет возврата к старому handoff. Рекомендация fresh отличается от соседней advisory-проекции auto.

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

`WorkStatePolicy.project_state` также собирает прежний полный ответ выбранного состояния из переданных записей и двух явных callback вычисления fingerprint/stable ids. Координатор сохраняет request scope, guards, validation/readiness/диагностику и получает action и project identity в исходном порядке. Сохранены порядок полей/вычислений, fallback, исключения и прежние ссылки; policy не получает Core, чтение файлов, кеш, новые зависимости конструктора или полномочия перехода. Прежние методы decision и completion не меняются.

`WorkRecordCatalogService` в `work/record_catalog.py` выполняет прежнее перечисление записей Work и построение активного/исторического списка через восемь обязательных отложенных зависимостей, используя WorkRecordReadPort либо прежний WorkInventory fallback. Сохранены отбор безопасной identity до загрузки Assignment, связь с Run, активность при pending completion, порядок fallback полей, дубликаты, исключения и повторные обращения к живым зависимостям. ProcessExecutionService сохраняет приватный фасад и существующие переопределяемые точки выбора/completion. Холодная frozen сборка не добавляет правила выбора или общий кеш.

`WorkSelectionService` выделяет существующую ответственность: выбор точной Work, session preference и сопоставление objective. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_work_selection_service.py`.

`ProcessSelectionService` выделяет существующую ответственность: выбор разрешённого процесса и формирование описаний кандидатов. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_process_selection_service.py`.

`ProcessPinReadService` выделяет существующую ответственность: чтение живого snapshot и построение process pin. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_process_pin_read_service.py`.

`WorkCompletionRequestService` в `completion/request.py` содержит прежнюю обработку `can_complete` и `complete`. Девять обязательных отложенных зависимостей сохраняют выбор Work, проверки закреплённого процесса и финальной стадии, порядок препятствий, ссылки на состояние и повторное завершение по уже записанному intent. Публичные методы координатора сохраняют сигнатуры и живые переопределения `can_complete`/`transition`. Неизменяемый сервис и его фабрика не выполняют ввод-вывод при создании; запись intent, блокировки, проверки доступа, переход и восстановление остаются у прежних владельцев.

`RunCompletionPolicy` выделяет существующую ответственность: проверка препятствий завершению Run и изменение статуса задачи в памяти. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_run_completion_policy.py`.

`CompletionIntentValidationService` выделяет существующую ответственность: валидация completion-intent с прежним порядком проверки принадлежности и конечного состояния. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_completion_intent_validation_service.py`.

`TransitionRejectionPolicy` выделяет существующую ответственность: классификация исправимых отказов перехода и построение ответа. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_transition_rejection_policy.py`.

`WorkBoundaryAdvisoryService` выделяет существующую ответственность: рекомендации на границе процессов и поиск advisory handoff. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_work_boundary_advisory_service.py`.

`CompletionDocumentService` выделяет существующую ответственность: формирование summary завершения и публикация существующего task index. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_completion_document_service.py`.

`CompletionIntentBuilder` выделяет существующую ответственность: построение самодостаточного completion-intent до конечных записей. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_completion_intent_builder.py`.

`CompletionIntentReadService` выделяет существующую ответственность: разрешение пути completion-intent и защищённое чтение живого journal. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; запись, locks, access checks и recovery остаются у прежних владельцев. Проверки: `tools/smoke_completion_intent_read_service.py`.

`CompletionIntentReplayService` выделяет существующую ответственность: упорядоченный replay completion-intent через существующие операции хранения и events. Зависимости передаются явно и закреплены на одну операцию; импорт Core или транспорта не требуется. Приватные методы фасада и переопределения callbacks сохранены; решение о восстановлении, блокировки и проверки доступа остаются у прежнего координатора; запись и события выполняются прежними адаптерами. Проверки: `tools/smoke_completion_intent_replay_service.py`.

`WorkTransitionCommitService` фиксирует уже разрешённый переход через явные callbacks существующих операций. Сохранены история этапа, порядок записи Run/Assignment, completion intent/replay, повторное чтение state, проекции, события и рекомендации на границе процесса. `ProcessExecutionService.transition` остаётся владельцем проверок доступа и охватывающей run lock; его конструктор и входы транспортов не меняются. `build_work_transition_commit_service` собирает зависимости без I/O. Проверки порядка публикации, обязательных отказов и поздних переопределений фасада: `tools/smoke_work_transition_commit_service.py`.


`work.records` владеет `YamlWorkRecordReader` и `CurrentWorkService`. Обычная сборка
напрямую использует Core `YamlDocumentReader`, YAML fallback, привязанные к проекту
пути и актуальный `WorkInventory`; универсальный старый Core читателям не передаётся.
`LegacyWorkReadAdapter`, `WorkReadCorePort` и неиспользуемая внутренняя facade
`governed_work_summary` удалены. Bootstrap/context/start вызывают методы этих
читателей Core. `FreshSessionBoundaryReadService` использует Core документы и rel.
Raw чтение Run/Assignment координатора также использует Core YAML; оставшиеся
lifecycle/admission/completion callbacks требуют следующих переносов. Внешний
CLI/MCP/Daemon контракт сохранён. Этот срез не доказывает независимость всего
bootstrap или координатора от legacy.

`agents.presence.AgentPresenceReader` владеет существующими путями presence,
живым чтением JSON, дедупликацией canonical/legacy записей и точным выбором сессии.
Он получает корень рабочего места и использует конкретные реализации Core для
идентичности и файлов. Функции монолита вызывают его методы. Общий digest точной
идентичности в `common.ids` также используется для путей chat transcripts.
Форматы, неоднозначность, неизвестные поля и ошибки чтения сохранены. Запись
attendance, expiry, binding, leases и ограниченное наблюдение Runtime остаются
у действующих владельцев.
Runtime Host, session read models и `RuntimeProcess.status_payload` вызывают
reader напрямую в десяти местах чтения presence. Импорты остаются внутри
операций: адаптеры по-прежнему загружаются до Core bootstrap. Stale-обновления
и их внутренние чтения сохраняют своего владельца; два чтения Work state
остаются самостоятельными живыми чтениями. CLI wrappers, bounded metrics,
attendance mutations и наблюдательный обход organized sessions остаются
явными следующими областями миграции.

`chat.transcripts.ChatTranscriptReader` владеет существующими путями transcripts
и живым чтением сообщений точно выбранной сессии. Его конкретный стандартный
`common.ndjson.NdjsonReader` владеет общим разбором NDJSON, включая исходные номера
строк и записи об ошибках разбора. Функции путей, сообщений и разбора в монолите
вызывают методы Core; чтение сессии Runtime и резервная проверка дубликатов
обращаются к Chat reader напрямую. Сохранены порядок legacy-before-canonical,
дедупликация по первому ID, неизвестные поля, непрозрачные идентификаторы,
декодирование и обработка ошибок. Авторизация сессии, страницы, запись сообщений,
оформление экспорта и ingress provenance остаются у действующих владельцев;
независимость всей цепочки здесь не заявляется.

`resources.catalog_read.WorkplaceSearchCatalogReader` владеет живым каталогом
физического поискового индекса Workplace: манифестами зарегистрированных пакетов,
knowledge packages активных официальных пакетов, проекцией ресурсов, шаблонами
и детерминированным fingerprint снимка. Его конкретные зависимости — пути
Workplace/distribution и `YamlDocumentReader`. Он использует существующий
`WorkspacePathReferenceReader` и единственный обход официальных пакетов
в `process_catalog.service`. Конструктор не читает документы и не сканирует
каталоги. Зависимостей от монолита, Runtime и Ledger у этого reader нет.

Совместимые функции каталога и проекции в монолите делегируют работу Core.
Обслуживание индекса Workplace, поисковая проекция сессии и сборка ResourceSearch
обращаются к конкретному каталогу напрямую. Авторизация по снимку проекта,
проверки свежести, порядок запросов и ошибок, а также владение SQLite сохранены.
`LegacyResourceSearchReadAdapter` пока передаёт отдельную легаси-зависимость
`project_context_check_result`: перенос каталога не завершает миграцию всего
ResourceSearch или монолита. Reader и общая проекция остаются предварительными
внутренними интерфейсами.

`project.snapshot_sources.ProjectSnapshotSourcesReader` владеет упорядоченными
живыми fingerprints источников, которые используют сборка снимка проекта и
проверка свежести. Его зависимости — конкретные readers метаданных проекта,
документов и raw-byte digests. Разрешение связанных manifest references
принадлежит `ProjectMetadataReader`. Выбор активных официальных пакетов с прежней
list-only семантикой принадлежит
`process_catalog.official_read.OfficialProcessPackReader`, который использует
единственный существующий обход manifests. Этот owner общий для источников
снимка, каталога Workplace и Runtime process resolution. Нормализация scalar
entries в других правилах каталога не меняется. Конструкторы не читают файлы и
не сканируют каталоги.

Восемь совместимых функций источников, ссылок и пакетов в монолите делегируют
Core. Две реальные точки сбора источников и Runtime consumer активных пакетов
обращаются к конкретным readers напрямую. Эти readers не принимают монолитный
Core или transport callbacks. Общая сборка snapshot, freshness policy/readiness
и другие Runtime bindings ещё имеют легаси-зависимости: срез не завершает эти
службы или какой-либо OOP-эпик. Новые readers — предварительные внутренние
интерфейсы; форматы записей, ошибки и чтение текущего содержимого сохранены.

## Правила готовности проекта

`project.readiness.ProjectContextReadinessPolicy` владеет существующими алгоритмами
execution и resource readiness. Построитель snapshot прямо вызывает методы
`execution` и `resources`. Обычный экземпляр не выполняет I/O и не хранит данные
запроса; его можно импортировать без CLI и Runtime. Порядок blockers, устранение
повторов capabilities, ошибки и поверхностное копирование conflict values сохраняются.

Полный freshness checker, classification и resource resolution, построение и
публикация snapshot ещё содержат legacy обязанности и callbacks. Этот ограниченный
перенос не завершает этих владельцев или какой-либо OOP эпик.


`project.source_check.ProjectSnapshotSourceCheckService` владеет существующим
сравнением сохранённых fingerprints с текущим содержимым источников. Freshness
checker вызывает его напрямую на месте прежнего inline алгоритма. Сервис использует
конкретный `ProjectSnapshotSourcesReader`; конструктор не выполняет I/O, а каждое
сравнение читает источники после нормализации записанных значений. Порядок причин,
дубликаты, исключение package-источников и исходные ошибки сохранены. Построение
snapshot сохраняет самостоятельное чтение источников. Общая координация и policy
полного checker, определение classification, разрешение ресурсов, построение и
публикация snapshot ещё сохраняют свои legacy bindings.


`project.resolved_comparison.ProjectSnapshotResolvedComparison` владеет прежним
сравнением classification и resolved resources двух переданных snapshots.
Конкретный `resources.versioning.ResourceVersionPolicy` без состояния владеет
общим числовым и лексическим алгоритмом версий для comparison, selection,
constraints и update candidates. Все найденные consumers используют этих
владельцев; старые внутренние key/index/version helpers удалены. Конструкторы
не выполняют I/O; порядок, дубликаты, warnings и исходные ошибки сохранены.
Сбор источников, полный checker status/policy, построение и публикация snapshot
ещё сохраняют существующих владельцев и legacy bindings.


`project.context_sources.ProjectContextSourcesReader` владеет прежними записями
источников широкого контекста и их упорядоченным живым сбором. Context resolution,
compilation и существующий startup smoke вызывают его напрямую; два устаревших
внутренних source helpers удалены. Reader использует конкретные metadata/YAML,
digest и path owners; конструктор без I/O, parsed documents не удерживаются.
Предпочтение root AGENTS, PF fallback, optional records, дедупликация по первому
resolved path, порядок, живые hashes и исходные ошибки сохранены. Полный checker,
построение и публикация snapshot сохраняют существующих владельцев.


Этот же reader владеет прежними проекциями `fingerprints` и `texts`. Построение
контекста использует один экземпляр на операцию для inventory и обеих проекций;
два старых внутренних helper удалены. Порядок ключей, замена дубликатов, исходные
преобразования строк, UTF-8 replacement и приоритет ошибок сохранены. Текст файлов
читается заново после сбора fingerprints; входы и результаты не удерживаются,
атомарность общего снимка не добавлена.

`project.context_rules.ProjectContextRules` владеет существующим разбором текстовых
списков, объединением разрешённых и запрещённых действий и оформлением отчёта
конфликтов. Чтение capabilities, построение snapshot и сборка широкого контекста
обращаются к нему напрямую; три устаревших внутренних helper удалены. Владелец
не выполняет I/O и не хранит входы или результаты. Текстовый разбор, defaults,
порядок, исходные ошибки и байты отчёта сохраняются. Полная сборка контекста,
проверка актуальности и публикация остаются у прежних владельцев.

`documents.answers.AnswersDocumentReader` владеет прежним строгим чтением answers:
отказами для отсутствующего файла и секретных значений, строгим декодированием
UTF-8, возвратом только YAML mapping и прежним резервным разбором при
`ModuleNotFoundError` через простой Core-парсер. Все потребители answers,
включая инициализацию проекта, обращаются к нему напрямую; старый внутренний
loader удалён. Проверка и скрытие секретных значений в CLI используют те же
определения шаблонов. Отличия его ошибок от политики `YamlDocumentReader`
сохранены.

`project.capability_registry.CapabilityRegistryReader` владеет извлечением
capability values и упорядоченной картой провайдеров из реестров tools/MCP
рабочего места и проекта. Все потребители значений и карты обращаются к нему
напрямую; два старых helper удалены. Стандартная сборка использует конкретные
`AnswersDocumentReader` и `ProjectMetadataReader`, не зависит от CLI и ничего
не читает при создании. Порядок рабочего места перед проектом, замена значений
и порядок ключей, фильтрация статусов, преобразования строк и пропуск только
`SystemExit` сохраняются. Каждый вызов читает текущие данные, не удерживая
документы или результаты. Доступность провайдера по-прежнему не даёт разрешения
на его исполнение.

## Политика контекста проекта и выбор ресурсов

`project.context_policy.ProjectContextPolicy` владеет прежним вложенным слиянием
переопределений, настройками контекста по умолчанию и выбором действия по состоянию
актуальности. Инициализация проекта, построение snapshot и проверка freshness
вызывают владельца напрямую. Настройки координации, порядок переопределений,
совместное использование вложенных значений и резервные действия сохраняются.

`project.resource_snapshot.ResourceSnapshotRules` владеет настройками `versioning`
и `retention`, объявленной версией и поколением (`generation`), fingerprints,
идентификаторами экземпляров, проекциями ресурсов, настройками индексирования
по умолчанию и общей оценкой воспроизводимости. Порядок полей, резервные значения,
исходные ошибки и различие между заимствованными значениями и копированием
метаданных остаются прежними. Класс не выполняет I/O.

`project.knowledge_selection.KnowledgeResourceSelector` владеет проекцией требований
контекста, ограничениями и префиксами версий, выводом версий платформ, прежними
правилами выбора требований и явным выбором ресурсов. Стандартная сборка использует отдельные для
каждого экземпляра конкретные `ResourceVersionPolicy` и `ResourceSnapshotRules`.
Создание не выполняет I/O; документы запроса и результаты не удерживаются.
CLI и существующий narrowing/search smoke вызывают владельцев напрямую;
17 внутренних функций и два набора правил ресурсов перенесены из CLI.

Это предварительные внутренние интерфейсы Core. Полная сборка context/snapshot,
сбор состояния freshness и публикация ещё сохраняют прежние обязанности в CLI. Этот
ограниченный перенос исходников не завершает OOP-эпики и не квалифицирует архив,
установленный Core, Runtime, подключённые хосты или производительность.

## Представление снимка контекста проекта

`project.snapshot_rendering.ProjectContextSnapshotRenderer` владеет существующим
формированием Markdown для снимка контекста проекта. Публикация снимка и
существующая smoke-проверка запуска агента напрямую вызывают метод `render`;
прежняя внутренняя функция удалена. Владелец без состояния сохраняет порядок
разделов и элементов, значения по умолчанию, Unicode, завершающий перевод строки,
прежние ошибки на некорректных данных и неизменность входного снимка. Он не читает
документы и не сохраняет входные данные или результаты.

Сборка снимка, определение актуальности и надёжная запись сохраняют свои
существующие обязанности. Перенос представления не делает эти пути независимыми
от прежней сборки зависимостей и не завершает ни один эпик OOP.

## Слияние параметров

`configuration.parameters.ParameterMergePolicy` владеет прежними правилами
рекурсивного слияния карт, слияния списков по ID, удаления и замены с упорядоченным
provenance. Метод экземпляра — `merge_maps(base, override, source_id, path="", provenance=None)`.
Владелец не хранит состояние слияния, не выполняет I/O и не зависит от CLI или
Host. Глубокое копирование, изменение переданного provenance, исходные ошибки,
порядок обхода и прежнее поведение дубликатов ID сохранены. Пять старых определений
parameter helpers удалены из `tools/processforge.py`.

Два прямых потребителя импортируют класс из модуля-владельца: `add_parameter_source`
в `tools/processforge.py` применяет policy при слиянии каждого источника и передаёт
существующий объект provenance; `work.context.build_context_fields` использует её
для слияния параметров неизменяемого контекста Assignment.

`build_context_fields` по-прежнему вызывает `core.add_parameter_source` и
`core.parameter_payload` для каскада источников process/stage/task. Нормализация
Assignment, пути и хеши snapshot, определение проекта/рабочего места, захват
источников и coordination также сохраняют прежние legacy-зависимости. Выделение
merge policy не делает полный компилятор контекста независимым от монолита.
Справочник описывает исходный код; приёмка архива, установленного Core, Runtime и
подключённых хостов остаётся отдельной.

## Проверка правил классификации и объявления артефактов процесса

`project.classification.ProjectClassifierRulePolicy` владеет прежним алгоритмом
правил через обычный метод экземпляра `matches(rule, available_paths)`; проверка
условий остаётся приватной. `inactive_official_classifier_hints` и
`classify_project` в `tools/processforge.py` вызывают владельца напрямую. Список
`when.all` имеет приоритет даже при пустом значении (результат false); непустой
`all` и `any` сохраняют короткое замыкание. Прежние проверки формы данных и
обработка непустой строки `exists` сохранены.

`common.paths.path_matches_pattern` — общий примитив для этой policy,
`ProjectDetectionService.group_matches` и `matches`. Он сохраняет нормализацию
обратных слешей и проверки стандартным `fnmatch.fnmatch` сначала полного пути,
затем его `Path(...).name`, включая платформенную семантику сравнения. `rel` не
изменён. Два старых определения классификатора и старое определение matcher
удалены из монолита; потребители явно импортируют модули-владельцы Core.

`process_catalog.artifacts.ProcessArtifactDeclarationPolicy` владеет обычными
методами экземпляра `defined_ids(process)`, `declared_ids(process)` и
`produced_ids(process)`. Core-проверки authoring и контракта процесса, а также
отчёт builtin catalog вызывают владельца напрямую; три старых
определения сбора ID артефактов удалены. Общие функции `common.values` сохраняют обработку
только списков, порядок преобразования и фильтрации string-list, строки через
запятую, различия dict/list, истинность ID, обработку дубликатов и прежний порядок
исключений. Остальные потребители монолита импортируют общие примитивы из
модулей-владельцев; два определения `as_list` с разным временем действия остаются
в монолите.

Обе policy не хранят состояние, не выполняют I/O и не импортируют монолит и не
вызывают его через callbacks. Загрузка реестров классификаторов, обход дерева и
активация остаются в legacy-путях CLI. Проверки контракта процесса и companion
принадлежат ProcessContractValidationService. Транзакции authoring, регистрация
каталога и активация сохраняют прежних legacy-владельцев. Выделение чистых policy не означает полного переноса
классификации или валидации, завершения OOP-эпиков или приёмки архива,
установленного Core, Runtime либо подключённых хостов.

## Построение процессов, evolve, документы драйверов и update-site

`process_catalog.authoring.ProcessAuthoringDefinitionBuilder` владеет методами
`defaults`, `normalize`, `build`, `normalize_transitions` и
`materialize_responsibility_boundaries`. Обычный конструктор использует конкретный
`process_catalog.evolution.ProcessEvolutionPolicy` с методами `default_block`,
`normalize_block` и `validate_block`. Сохранены новые значения по умолчанию при
каждом вызове, прежние ссылки на вложенные данные и места глубокого копирования,
неизвестные поля, обработка отключённого evolve и порядок проверок. Маршруты
переходов сохраняют общий словарь возврата. Полная проверка authoring и схем,
а также надёжная публикация остаются у прежних владельцев.

`runtime.drivers.RuntimeDriverDefinitionPolicy` владеет методами
`default_documents`, `default_registry`, `placeholder_errors`, `parse_limits`,
`start_readiness` и `validate`, а также прежними наборами зарезервированных
переменных среды и placeholders. Готовность документа проверяется без поиска
исполняемого файла. Сохранены свежие словари, сообщения и порядок проверки,
исходные ошибки и прежняя нормализация аргументов. Запуск процессов Runtime,
чтение реестра и жизненный цикл воркеров сохраняют существующих владельцев.

`maintenance.sites.UpdateSitePolicy` владеет методами `location`, `source_kind`,
`source_id`, `stable_key`, `record` и `policy`. Сохранены порядок ключей источника,
пробелы в непустом ID, приоритет переопределений, изменение общего вложенного
словаря политики и заимствованные значения каналов, родителя и локальных данных.
Класс использует `common.paths.rel` и не выполняет I/O. Поиск обновлений,
проверка схем, сеть, установка и восстановление остаются у прежних владельцев.

Общие примитивы имеют единственного владельца: `common.checks.Check` остаётся
изменяемым dataclass, а `check` переводит уровень в верхний регистр;
`common.ids` содержит `safe_id` и `title_from_id`, `common.values` — строгий
списочный `as_list` и прежний `string_list`. Все найденные потребители используют
конкретные классы или эти импорты. Прежние внутренние определения удалены без
обёрток. Перенос сохраняет внешние контракты 1.2.0 и подтверждён для исходников;
он не завершает OOP-эпики и не квалифицирует другие слои поставки.

## Представление, актуальный каталог драйверов и выбор candidates

`ProcessAuthoringDefinitionBuilder.from_definition` владеет прежним обратным
преобразованием определения процесса в authoring answers. Предыдущие методы
builder не изменены. `process_catalog.presentation.ProcessAuthoringRenderer`
содержит `questions`, `logic_review`, `agent_prompt` и `document`, сохраняя байты
текста и порядок вычислений. Небольшая каноническая функция
`process_catalog.coordination.process_coordination_requirements` и её набор
режимов используются также оставшимися потребителями монолита.

`runtime.catalog.RuntimeDriverCatalogReader(distribution_root)` использует
конкретные `YamlDocumentReader`, `ProjectMetadataReader` и
`RuntimeDriverDefinitionPolicy`. Ему принадлежат пути и записи реестров, пути
документов, строгое чтение, точный поиск зарегистрированного драйвера, разрешение
и нормализация ссылок, список ID. Сохранены первое подходящее совпадение,
упорядоченные замены, прямые пути, встроенные значения, неизвестные поля и
исходные отказы. Конструктор не выполняет I/O; операции читают текущие файлы
без хранения разобранных документов. Монолит и существующий поиск драйвера
в MCP вызывают этого владельца. Адаптер MCP сохраняет проверку ID перед
отложенным импортом, порядок bootstrap и привязанные project/workplace.

`evolution.candidates.KnowledgeCandidateTargetingPolicy` владеет прежними
проекциями ID, target и destination, готовностью promotion/generalization
и упорядоченной проверкой targeting. Он сохраняет ссылки на вложенные словари
и использует канонические checks, идентификаторы, string-list и существующие
типы evolve targets. Новый пакет ответственности имеет минимальный initializer.
Полная очистка кандидатов, публикация/экспорт и lifecycle остаются у прежних
владельцев.

`maintenance.versions.UpdateVersionSelectionPolicy` использует конкретные
`ResourceVersionPolicy` и `UpdateSitePolicy` для прежнего поиска latest, двух
форматов версий manifest, выбора версии и ID кандидатов. Вложенные ссылки,
общий словарь subject, стабильная сортировка и warnings сохраняют прежнее
поведение. `maintenance.presentation.UpdateAssessmentRenderer.render` владеет
исходным текстом assessment. Получение данных, координация обновления, установка
и восстановление остаются у прежних владельцев. Эти внутренние интерфейсы
фиксируют владение исходниками; внешние команды, схемы MCP и приёмка слоёв
поставки сохраняют существующие контракты.

## Поля Work, coordination, общие privacy и контракты источников

Существующий `work.context_documents.ContextContractInputs` дополнен восемью
прежними операциями: ключи путей Assignment, проекция write scope, признаки glob
и overlap, зависимости, наблюдение файлов required sources, coordination капсулы
и сопоставление пути со scope. Поля, frozen-конструктор и 20 предыдущих методов
не изменены. Нормализация переиспользована; две старые обёртки монолита удалены.
Компилятор контекста вызывает проекцию coordination напрямую на прежнем месте.
Платформенная семантика и пустые scopes сохранены; доступ, admission, lifecycle
и остальные зависимости компилятора остаются у существующих владельцев.

`project.coordination.ProjectCoordinationReader` владеет прежними defaults,
нормализацией режимов и чтением project/workplace configuration. Конкретные
читатели YAML и метаданных проекта сохраняют актуальное чтение, поверхностное
слияние director, неизвестные поля, свежие defaults и порядок отказов. Reader
не хранит проект, Work или разобранную конфигурацию. Общая сборка effective
coordination и операции Director остаются у прежних владельцев.

`common.privacy` содержит `BACKSLASH`, `LOCAL_PATH_PATTERNS`,
`SECRET_VALUE_PATTERNS`, `is_public_path_safe` и `contains_secret_value`.
`AnswersDocumentReader` использует канонические данные с прежним алгоритмом
класса. `evolution.privacy.EvolvePrivacyPolicy` владеет `findings`, `text` и
`value`, сохраняя regex/flags, замены, рекурсию, ключи словарей, идентичность
tuple и исходные ошибки. Host вызывает канонический secret-предикат после
прежних фильтров автоматического содержимого. Короткое замыкание, bootstrap
и все проверки authentication/provenance/hash сохранены.

`maintenance.source_contracts.UpdateSourceContractPolicy` владеет прежними HTTPS
defaults, формой remote/artifact URL, env-reference и source checks, проверкой
реестра и сортировкой. Сохранены изменение переданного списка checks, различия
типов/truthiness, исходные ошибки и порядок проверок. Schema-based overrides и
полная проверка normalized manifest вызывают эти общие методы из прежних
владельцев. Новые scanner/trust/authorization/update правила не добавлены.
Перенос сохраняет модульные аннотации и внешние контракты 1.2.0; доказательства
относятся к квалифицированному срезу исходников.

## Выходы Work, обнаружение платформы, окружение воркера и схемы

`work.outputs.WorkOutputPolicy` владеет `waivers`, `path`, `task_path`,
`expected_report` и `default_report`. Нормализация использует существующий
`ContextContractInputs`. Сохранены проверки traversal, drive и абсолютных путей
до разрешения, containment, исходные ошибки и значения по умолчанию.
Нормализация required outputs вызывает прежнего владельца Core напрямую.
Та же политика владеет `checks` обязательных выходов и verification `fingerprint`;
lifecycle остаётся у прикладного сервиса. Host и остальные потребители вызывают
политику на прежних местах защитных проверок. Необязательные зависимости
прикладного сервиса описаны ниже.

`project.detection.ProjectDetectionService` владеет `files`, `group_matches`
и `matches`, используя канонические `common.paths` и `common.values.list_value`.
Общий список файлов сохраняет прежние исключения компонентов пути и отличается
от обхода классификатора. Сохранены порядок файлов, пределы чтения, буквальный
поиск при ошибке regex и наблюдение актуальной файловой системы. Кеш разобранных
данных или проверка свежести только по метаданным не добавлены. Чтение и активация
классификаторов остаются у прежних владельцев.

`runtime.environment.WorkerEnvironmentPolicy` владеет `minimal`, `build`,
`materialize` и `expand`, переиспользуя reserved keys из `runtime.drivers`.
Сохраняемые данные команды содержат прежние значения PF и явную конфигурацию;
окружение хоста наследуется только при запуске. Рекурсия placeholders,
преобразования, отказы по reserved keys и исходные ошибки сохранены. Создание
процесса, состояние попытки, сбор результата и восстановление остаются
у существующих владельцев.

`maintenance.schema_checks.UpdateSchemaChecks(distribution_root)` владеет
`type_matches`, `resolve_ref`, `validate`, `append` и `require`. Это прежнее
подмножество JSON Schema с исходным порядком сообщений и исключениями.
Конструктор не выполняет I/O; каждая проверка заново читает файлы схем.
Координация обновлений, сеть, установка и восстановление остаются у прежних
владельцев. Приёмка относится к исходникам; архив, установленный Core, Runtime
и реально подключённый хост проверяются отдельно.

## Пути Work, команды воркеров и актуальные каталоги

`work.paths.WorkPaths` владеет путями документов Run и Assignment, артефактов,
сводок, handoff, worker prompts и упорядоченными путями попытки. Каталог Run
и handoff сохраняют допустимые generated ID с повторными дефисами; пути
Assignment и agent/task используют прежнюю отдельную нормализацию `safe_id`.
Строгая проверка пути Assignment в `ContextContractInputs` остаётся отдельной.
Конкретный `ProjectMetadataReader` предоставляет flow root без I/O конструктора.

`runtime.command.WorkerCommandBuilder(distribution_root)` владеет `sandbox` и
`build`, используя существующих владельцев путей, выходов, окружения, driver
limits и нормализации контекста. Проверка выходов предшествует variables и
окружению. Placeholders, model arguments, prepared wrapper, разрешение путей
и поля команды сохраняют исходный порядок. Проверка terminal admission
наблюдает перенесённый builder и сохраняет прежние assertions. Запуск процесса,
блокировки, состояние попытки, сбор и восстановление остаются у прежних владельцев.

`project.platforms.PlatformContractReader(distribution_root)` владеет ID,
поиском реестра, seed/project путями, чтением записей, overlay index и fallback.
Он переиспользует YAML Core и `WorkspacePathReferenceReader`, сохраняя порядок
seed/project/workplace, aliases, дубликаты, неизвестные поля, disabled/missing
и ссылки на исходные вложенные значения. Операции читают актуальные файлы без кеша.

`maintenance.documents.UpdateDocumentReader(distribution_root)` владеет путями
реестров обновлений, мягким чтением YAML, doctor YAML/schema checks, поиском путей
manifest, списками registry paths, update index, локальными file URL и чтением
YAML/JSON документов и текста. Переиспользованы прежние YAML/path/schema owners.
Мягкое чтение отбрасывает ошибки YAML; index сохраняет прежний error sentinel;
doctor может добавить ошибки схемы и всё равно вернуть разобранный словарь.
Конструктор не выполняет I/O. Сеть, запись и lifecycle обновлений остаются
у прежних владельцев. Egress и prepared inputs используют канонические пути
Work, сохраняя остальные неперенесённые зависимости. Приёмка ограничена
исходниками; более поздние слои поставки и OOP-эпики проверяются отдельно.

## Готовность выходов, выбор драйвера и проверки

`WorkOutputPolicy.checks` и `fingerprint` сохраняют пропуск optional outputs,
waivers, различия missing/pending/invalid, актуальное чтение и точное JSON/hash
кодирование. Прежние поля, конструктор и методы путей не меняются.
`ProcessExecutionService` получает независимые необязательные keyword-only
callables `output_checks` и `verification_fingerprint`. По умолчанию используются
методы Core, явный `None` означает недоступность. Frozen/repr/compare и три
позиционных аргумента сохранены. Projectors сохраняют guards, reasons и
идентичность исключений; неиспользуемые capabilities остаются ленивыми.
Зависимости событий и журнала сохраняют прежнюю сборку.

`runtime.selection.RuntimeDriverSelectionService(distribution_root)` владеет
`for_task` и `for_worker_state`, сохраняя чтение сохранённой команды, копирование
direct path, fallback и порядок проверок/ошибок. Существующий
`ProjectMetadataReader.workplace_manifest()` владеет локальным поиском manifest
с проектом, привязанным к reader. Он отличается от широкого автоматического
разрешения workplace. `common.json_io.json_read` сохраняет прежние raw JSON types
и исходные ошибки чтения/разбора.

`project.platform_policy.PlatformContractPolicy(catalog)` получает конкретный
`PlatformContractReader` для канонических ID. Ему принадлежат нормализация ссылок,
extends/requires и проекции required/recommended/optional ресурсов с прежними
различиями типов/truthiness, сортировкой, dedup и includes. Разрешение иерархии
и каталог пакетов проекта используют конкретных владельцев, описанных ниже.

`process_catalog.validation.ProcessAuthoringValidationService` владеет `logic`,
`files` и `paths`, используя готовые evolution/artifact policies и канонические
workflow/iteration constants. Порядок checks, вложенная проверка ID, warnings,
companion root и наблюдение файлов сохранены. Общая
`common.privacy.public_yaml_has_private_path` сохраняет прежнюю сериализацию
и предикат. Полная проверка process contract использует конкретного владельца ниже; проверка
route-map, публикация и recovery остаются у существующих владельцев. Внешние контракты 1.2.0 и приёмка более
поздних слоёв поставки проверяются отдельно.

## Пакеты проекта, иерархия платформ, семантика процессов и планы работников

`resources.project_packages.ProjectPackageCatalogReader(distribution_root)` владеет
`workplace_roots`, `workplace_root_paths`, `candidates`, `index`, `dependencies`
и `root_from_entry`. Проект и workplace передаются на каждой операции. Поиск
сохраняет порядок обхода, устранение повторных разрешённых путей и добавления из
активных официальных пакетов. Индекс проекта сохраняет последнее совпадение и
отдельную запись дубликатов; поисковый каталог workplace по-прежнему сохраняет
первое совпадение. Кеша документов и чтения в конструкторе нет.

Перенесённый `PackageRootResolution` сохраняет имя класса, поля, аннотации,
значения по умолчанию и представление. Для записи корня используется готовый
алгоритм `WorkspacePathReferenceReader`, затем явно сопоставляются поля обычной
записи с сохранением ссылок warnings/entry. Прежняя частная модель snapshot и её
потребители не меняются; правила разрешения путей не копируются.

`project.platform_resolution.PlatformContractResolver(distribution_root)` владеет
прежними рекурсивными операциями `resolve` и `merge_ids`. Он использует конкретных
владельцев каталога, проекций платформ и пакетов. Сохраняются порядок обхода и
циклов, различия ресурсов extends и required-platform, ссылки overrides, порядок
конфликтов, сортировка результата и очередь зависимостей пакетов.
`common.values.parameter_payload` возвращает прежний исходный словарь параметров.
Сборка контекста Work использует этот примитив напрямую; остальные её зависимости
остаются неперенесёнными.

`process_catalog.semantics.ProcessSemanticPolicy` владеет полнотой авторинга,
семантической картой и проекциями процесса, строк, событий, объектов и сравнением.
`presentation.process_parity.ProcessParityRenderer` владеет прежними Markdown-
отчётами `import_report` и `parity_report`. Их текст, приоритет ошибок и
предупреждений, различия отсутствующих исходных полей сохранены.

`runtime.worker_plans.WorkerPlanPolicy` владеет начальными планами, проекциями
работников/подагентов и зависимостей, рекурсивной достижимостью, буквальным правилом
пересечения записей и `task_dependencies_done`. Последняя операция использует
актуальные пути Work и строгое чтение YAML. Исполнение, scopes/leases, блокировки,
жизненный цикл и восстановление остаются у прежних владельцев. Внешнее поведение
1.2.0 и приёмка более поздних слоёв поставки проверяются отдельно.

## Корни пакетов, выбор платформ, реестры обновлений и контракты процессов

`ProjectPackageCatalogReader` также владеет чтением реестра корней, разрешением
корней и путей, поиском и загрузкой манифестов через готовый конкретный
`WorkspacePathReferenceReader`. Алгоритмы переиспользованы; публичная модель корня
сохраняется через одно явное сопоставление полей. Частная модель snapshot и её
потребители не меняются. Прежние методы каталога, поля и конструктор сохранены.

`project.platform_selection.ProjectPlatformSelectionService(distribution_root)`
владеет прежним выбором обычных и производных платформ, подсказками типов проекта
и родителей, актуальным обнаружением, находками реестров, сопоставлением bindings
и правилами запрета базовой технологии. Используются конкретные читатели и явные
проект/workplace на операции. `AnswersDocumentReader.strings` владеет рекурсивным
сбором строк ответа; `PlatformContractReader.normalize_id_pair` — прежней парой ID.
Нормализация и сопоставление подсказок находятся в `project.classification`,
`common.values.registry_ids` сохраняет буквальную проекцию реестра. Прежние методы
и данные владельцев не меняются. Чтение прежних метаданных MCP не добавляет
использование MCP-ресурсов.

`YamlDocumentReader.policy(name, root=None, *, distribution_root)` владеет прежним
поиском policy-документа. Обязательный аргумент по имени заменяет глобальный ROOT,
не захватывая фиктивный проект и не меняя конструктор. Guards файлов, мягкие ошибки
YAML и возвращаемые значения сохранены; потребители передают действительный корень
дистрибутива. Остальные методы документов остаются прежними.

`maintenance.registries.UpdateRegistryReader(distribution_root)` владеет записями
манифестов, overrides, поиском установленных subject и выбором пути установки.
`UpdateDocumentReader` также владеет путями runtime/candidates/notifications.
Порядок поиска и приоритет overrides, ссылки на записи, устранение повторов только
пакетов и порядок override/installed/fallback сохранены. Эти операции читают и
разрешают пути; установка, запись версии с timestamp и lifecycle обновлений
остаются у прежних владельцев.

`process_catalog.contracts.ProcessContractValidationService(distribution_root)`
владеет полной проверкой контракта процесса через готовых владельцев metadata,
evolution, артефактов, авторинга и route-документов. `ProcessRouteDocumentReader`
владеет путём и мягким чтением карты. Канонические metadata и stable predicate
находятся в `process_catalog.service`; общие handoff modes — в `contracts`.
Порядок guards/checks/отказов и наблюдений файлов, severity strict/stable, неизвестные
поля, приоритет companion/templates и defaults карты сохранены. Проверка самой
route-map, исполнение handoff, callbacks/транзакции авторинга, lifecycle,
блокировки, recovery и приёмка последующих слоёв остаются отдельной работой.

## Проверка планов, записей и чтение маршрутов и handoff

`runtime.worker_validation.WorkerPlanValidationService(distribution_root)` владеет
прежними проверками плана, фильтрацией дополнительных ключей и проверкой отчётов
подагентов. Он использует готовые ContextContractInputs, RuntimeDriverCatalogReader,
WorkerPlanPolicy и ScopeConflictService с фактическим проектом на операции.
Буквальные проверки типов, повторные чтения драйверов, исключения зависимостей,
конфликты областей и рекурсивные наблюдения отчётов сохраняют прежний порядок.
Четыре набора полей плана принадлежат этому модулю. WORKSPACE_ACCESS_KEYS и обе
нормализации используют готовый work.context_documents напрямую; старые обёртки
и дублирующий tuple удалены, включая три обращения других компонентов Core.

`project.hooks.HookConfigurationReader` владеет путём hooks.yaml и прежними
упорядоченными проверками формы. `common.record_validation.RecordValidationPolicy`
владеет обязательными полями event/chat, прежним выражением типа события и общей
проверкой секретов. Сериализация JSON и её исходные ошибки сохранены.
Отправка hooks, журналы и эффекты остаются у действующих владельцев.

`process_catalog.routes.ProcessRouteService(distribution_root)` владеет текущим
поиском и проверкой маршрута и проекцией требуемой роли. Используются готовый
читатель маршрутов, общие режимы и проверка схемы. `process_catalog.handoffs.HandoffDocumentReader`
владеет каталогом, путём и мягким чтением handoff через фактические metadata
проекта и документы. Первое совпадение, ссылки на словари, порядок проверок
и отказы отсутствия сохранены. Запись и исполнение handoff, leases, continuation,
транзакции процесса и recovery остаются у действующих владельцев.

`maintenance.validation.UpdateDocumentValidationService(distribution_root)`
владеет прежними проверками overrides и нормализованного манифеста через
конкретные schema/source-contract policies. Выражение SHA-256 сохранено.
UpdateRegistryReader также владеет отдельной проекцией установленных версий;
UpdateDocumentReader — путём и мягким чтением staged record. Конструкторы
и все прежние методы читателей сохранены. Поиск, запись, установка, ввод-вывод
артефактов, сеть и получение времени остаются у прежних владельцев.

## Документы платформ, проверки реестров и аудит каталога

`project.platform_documents.PlatformDocumentBuilder` владеет прежним построением
списка путей, байтов и заметок документов платформы. Литералы YAML и Markdown,
порядок результатов и исходные ошибки обращений сохранены; метод возвращает
данные и не записывает файлы. Publication авторинга платформ сохраняет владельца; семантическая проверка
перенесена в PlatformContractValidationService, описанный ниже.

`project.registry_checks.WorkplaceRegistryValidationService(distribution_root)`
владеет текущими проверками путей реестров и корней пакетов через готовые
WorkspacePathReferenceReader, ContextContractInputs и ProjectPackageCatalogReader.
Фактический workplace передаётся на операцию. Правила aliases/default/status/
writable, дубликаты, наблюдения файлов и порядок предупреждений сохранены.
`common.yaml_dump` владеет точными прежними format_scalar и рекурсивным dump_yaml;
все фактические потребители Main/Runtime/process execution используют этого владельца.
Фабрика yaml_formatter без аргументов и callback форматирования с одним аргументом
сохраняют прежнюю форму. Сериализатор не подменяется, Runtime не запускается.
`common.text` владеет прежними ensure_trailing_newline и check_with_hint.
Сборка публикации капсулы вызывает канонические newline/YAML formatters из тех же
callback с одним аргументом; остальные legacy-зависимости сохраняют владельцев. Порядок публикации
и ошибок не меняется.

`process_catalog.audit.BuiltinProcessCatalogAuditService(distribution_root)`
владеет упорядоченным отчётом builtin catalog через конкретный читатель каталога
на операцию, contract/authoring/artifact policies и канонические metadata.
Плоский отсортированный индекс root/packages/*.yaml сохраняет отличие от полного
индекса пакетов проекта. Пропуск internal в public-режиме, official companion roots,
счётчики, повторные наблюдения и объединение предупреждений прежние.
Чистая проекция process_catalog_contexts находится в существующем service.py;
все его прежние определения и данные сохранены.

`project.setup.WorkplaceSetupProposalBuilder` владеет прежним словарём предложения
настройки и Markdown через ProjectCoordinationReader. Defaults, path placeholders,
преобразование списков, ссылки на поля, порядок и отказы неверного режима сохранены.
Конструкторы не выполняют ввод-вывод. Настройка, транзакции авторинга, блокировки, recovery и последующие слои
приёмки сохраняют владельцев. Обновление реестра — в WorkplaceRegistryWriter.

## Запись реестров, поиск шаблонов и проверки платформ

`project.registry_write.WorkplaceRegistryWriter(distribution_root)` владеет
прежним обновлением реестра. Сохранены карта схем, проверки и исходные отказы,
UUID staging рядом с назначением, os.replace и очистка finally. Новых блокировок,
повторов или правил атомарности нет. Общий upsert_resource находится в прежнем
common.values, все существовавшие определения которого сохранены.

`project.templates.TemplateCatalogService(distribution_root)` владеет выбором
корня шаблонов и поиском манифеста через WorkspacePathReferenceReader и
WorkplaceRegistryWriter. Read не записывает; write сохраняет fallback upsert
перед проверкой выбранного ID и прежний порядок mkdir. Приоритет кандидата,
первое совпадение реестра и прежние правила путей сохранены без новых ограничений.

`project.platform_validation.PlatformContractValidationService(distribution_root)`
владеет прежней полной семантической проверкой через конкретные владельцы
контрактов, разрешения платформ, выбора, пакетов и шаблонов. Порядок сообщений,
повторные чтения, обязательность ресурсов, циклы и falsey fallback сохранены.
Чистые policy_entries/policy_id_matches находятся в common.policies; остальные
потребители Main используют эти же общие функции.

`project.requirements.PlatformDependencyPreflightService(distribution_root)`
владеет прежним preflight зависимостей и прямым чтением ID реестров workplace.
Порядок отсутствующих ресурсов, дубликаты, чтения tools/MCP и исходные отказы
сохранены. Конструкторы не читают файлы и не удерживают документы проекта.
Все фактические потребители переведены в этом срезе. Publication/транзакции
авторинга и невыбранные recovery-пути сохраняют прежних владельцев. Source-only
рефакторинг не завершает OOP-эпики и приёмку архива/установки/Runtime/connected host.

## Ресурсы, проверки пакетов и worker assignment prompt

`resources.records.ResourceRecordService` владеет прежними load/index defaults,
ссылками на зарегистрированные корни, публичным path_ref и нормализацией записей.
Точный набор HEAVY_RESOURCE_KINDS расположен рядом. Алгоритмы путей и snapshot
переиспользуют готовых владельцев. Ссылки на вложенные поля, скрытие приватных
путей, приоритет первого корня, unknown fields и неиспользуемый register_private_path
сохраняют прежнее поведение без новых записей.

`resources.package_checks.KnowledgePackageValidationService(distribution_root)`
владеет прежним doctor пакета, отдельным повторным чтением манифеста/схемы,
проверками ресурсов, индекса, приватности, navigation/dependencies/policy в прежнем
порядке. `resources.index_checks.KnowledgeResourceIndexService(distribution_root)`
владеет выбором пути индекса, проверкой path_ref в реестрах и индексами ресурсов
проекта через готовые containment/ID/package/registry owners. Ранний возврат для
package.yaml и необязательность локального индекса сохранены. Общая точная
path_is_relative_to находится в существующем common.paths.

`work.worker_assignment.WorkerAssignmentService` владеет строгим полным чтением
Assignment и прежним текстом worker launch prompt. Отказы missing/YAML, порядок
safe ID/путей, ветви prepared input, счётчики, разделы и newline сохранены.
Все шесть прежних Host/smoke потребителей используют Core reader; их остальная
логика и assertions не меняются. Конструкторы не читают и не удерживают документы.
Preparation/launch policy, запись индекса/timestamps, невыбранный authoring и
lifecycle/recovery сохраняют владельцев. OOP-эпики и последующая приёмка открыты.

## Данные и чтение авторинга, представление процессов и кандидаты

`authoring.plans` владеет прежними изменяемыми dataclass AuthoringWrite,
AuthoringEffect, AuthoringPlan и AuthoringPlanRenderer. Поля, defaults, ссылки
на callback-данные и отсортированный stdout сохранены. AuthoringInputService
в `authoring.inputs` владеет режимом, путями transaction/journal, незавершёнными
журналами и проверками/цепочками родителей. Перенесённый scope не исполняет
callbacks. Preflight, failure injection, staging/publication/commit/rollback
сохраняют владельцев. FileDigestReader получил два прежних raw-byte/guarded-file
метода; его streaming-метод и dataclass-контракт не изменились.

`process_catalog.examples` владеет точной process_yaml_content и построением
семи прежних документов примера через ProcessAuthoringExampleBuilder. Готовый
ProcessParityRenderer получил прежний индекс parity, общая aggregate_status
находится в common.status. Существовавшие методы, литералы, порядок, аннотации
и исходные ошибки сохранены.

`maintenance.candidate_read.UpdateCandidateReader(distribution_root)` владеет
прежним свежим JSON read/find через готовые пути UpdateDocumentReader и точные
существующие часы common.clock.now_utc. Конструктор не читает файлы/время.
Fallback missing/JSONDecodeError/non-dict, остальные ошибки, raw ID/first match
и unknown fields сохранены. Два authoring smoke используют канонические модели
и inputs после прежнего локального bootstrap; assertions, fixtures и матрицы
failure injection точны. Новых функций нет; OOP-эпики и поздняя приёмка открыты.

## Чтение сессий, каталог специализаций, кандидаты и перенос обновлений

ProjectSessionReadService владеет прежним regex статуса отчёта, порядком недавних
файлов и legacy freshness по подстрокам context-index. Он использует готовые
project metadata/source readers. Современный context freshness и report lifecycle
сохраняют владельцев; common.text владеет точной общей константой COLON_WS.

SpecializationCatalogReader(distribution_root) владеет прежними resource IDs,
registry paths, упорядоченными candidates с дедупликацией, manifest index и
выбором первого файла. Готовый WorkspacePathReferenceReader отвечает за guards,
containment и path constants; YAML/metadata owners переиспользованы. Фильтр
статусов candidates и нефильтрованный индекс с последним победителем сохранены
как разные алгоритмы. Неизвестные поля и повторные свежие чтения не изменены.

KnowledgeCandidateValidationService собирает готовые targeting/privacy policies
и прежние проверки в исходном порядке; evolution.validation владеет точным набором
категорий. Конструкторы не читают документы. UpdateTransferService переиспользует
site/document owners и сохраняет local copy2/HTTP stream, timeouts, границы
warnings/errors и эффекты destination. Новых retries, mkdir или проверки архивов
нет. Внешние контракты 1.2.0 сохранены; OOP-эпики и поздняя приёмка открыты.

## Журналы, источники параметров, проекции отчётов и входы проекта

AuthoringJournalStore владеет прежними data/plan writes журнала: mkdir, UUID
соседнего временного файла, serialization, replace и finally cleanup сохранены
в прежнем порядке с тем же приоритетом ошибок. Preflight, callback/effect
execution, publication и rollback сохраняют существующих владельцев.

ParameterSourceService владеет source records, workplace paths, накоплением
источников, чтением process parameters и requirements fingerprints. Готовые
path/YAML/digest/merge owners переиспользованы. Приватные markers, aliases,
порядок источников и свежие чтения сохранены. Work context вызывает службу
напрямую в трёх выбранных шагах; остальные обязанности явно не перенесены.

ReportProjectionReader владеет прежним разбором Markdown sections/boolean,
точной справкой capability waiver и resource report status. Aggregate smoke
подменяет канонический метод, сохраняя fixtures/assertions/restoration.
ProjectInitializationInputs владеет manifest project types, наборами разрешённых
типов, greenfield/brownfield и начальными defaults. Initialization consumer
вызывает её напрямую. Coordination modes/defaults имеют отдельный контракт.
Конструкторы холодные, корни явные. Source-only перенос сохраняет 1.2.0;
OOP-эпики и поздняя квалификация остаются открытыми.

## Настройка, правила, события и данные выполнения

Следующие двадцать ограниченных групп переданы конкретным владельцам Core.
Выбранные реализации и прежние алиасы вспомогательных функций удалены из Main;
потребители в CLI, Runtime, Core и проверках обращаются к модулям владельцев.

| Ответственность | Модуль и владелец |
| --- | --- |
| Ответы настройки рабочего места | `project.setup_answers.WorkplaceSetupAnswers` |
| Источники классификаторов и перечни файлов | `project.classifier_sources.ProjectClassifierSourceReader` |
| Роли путей и исключения сканирования | `project.scan_policy.ProjectScanPolicy` |
| Отбор исходников выпуска | `maintenance.release_sources.ReleaseSourcePolicy` |
| Переопределения проекта | `project.overrides.ProjectOverrideReader` |
| Поставщики возможностей и маршруты | `project.capability_resolution.ProjectCapabilityResolution` |
| Журналы событий ресурсов рабочего места | `resources.workplace_events.WorkplaceResourceEventJournal` |
| Происхождение выпуска в Git | `maintenance.release_provenance.ReleaseGitProvenance` |
| Сопоставление ресурсов рабочего пространства | `work.workspace_refs.WorkspaceAccessReferenceService` |
| Выбор хуков и подготовка их данных | `agents.hook_policy.HookDispatchPolicy` |
| Представление экспорта чата | `chat.export.ChatExportService` |
| Запись метаданных сессии | `agents.session_metadata.SessionMetadataWriter` |
| Построение и запись событий телеметрии | `agents.telemetry.TelemetryEventService` |
| Чтение и согласованность Run/task | `work.consistency.RunTaskInputReader`, `RunTaskConsistencyService` |
| Настройки оркестрации | `work.orchestration_config.OrchestrationConfigService` |
| Профили, планы и состояние supervisor | `runtime.supervisor_inputs.SupervisorInputService`, `SupervisorStateInputs` |
| Данные наблюдения за воркерами | `runtime.observation_inputs.WorkerObservationInputService` |
| Реестр агентов рабочего места | `agents.registry.AgentWorkplaceRegistry` |
| Состояние координации проекта | `project.coordination_state.ProjectCoordinationStateService` |
| Правила публичных исходников и кодировки | `maintenance.public_source_checks.PublicSourcePolicy` |

`resources.registries.WorkplaceRegistryReader` владеет прежним чтением реестров
и связанными правилами путей, которым не нужен корень проекта или дистрибутива.
Замороженный `WorkspacePathReferenceReader` наследует эти алгоритмы, сохраняя
поля и конструктор. Данные Run/task и supervisor также отделены от операций,
которым требуется явно заданный корень дистрибутива. Подстановка корня проекта
или текущего каталога вместо него не используется.

Общие простые функции находятся в `common.clock`, `common.json_io`,
`common.yaml_io` и `resources.buckets`. Точные константы правил расположены
рядом с владельцами. Изменяемый реестр отсоединённых процессов остаётся единым
объектом в `runtime.observation_inputs` для перенесённых и оставшихся операций.
Конструктор и match arguments ProcessExecutionService сохранены; закрытые поля
часов и путей событий получают конкретные операции Core без обращений к Main.
Управляемые тестовые зависимости перенесены с сохранением assertions и порядка
ошибок. Импорты Runtime следуют прежним проверкам и загрузке Core.

Алгоритмы, сигнатуры, данные ответов, ошибки, форматы документов, неизвестные
поля, порядок чтения/записи и свежие чтения YAML сохранены. Пометка индекса после
события ресурса действует по прежним правилам. Операционное наблюдение за
воркерами, материализация пересечений, оставшийся сценарий доступа к рабочему
пространству и lifecycle/recovery сохраняют прежних владельцев. Новых функций
продукта нет; OOP-эпики и приёмка архива, установки, Runtime и подключённого хоста
этими группами не завершаются.
