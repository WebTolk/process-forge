# Исследование MCP: описания инструментов, границы сервисов и возможность resources

**Статус:** исследование завершено. Продуктовые изменения не выполнялись.

Рекомендуемый следующий срез — уточнить описания существующих инструментов и выделить каталог MCP из транспортного модуля, сохранив опубликованное поведение. MCP resources технически реализуемы, однако выдача тел документов требует отдельного согласованного контракта доступа. Простое преобразование результата `pf.work.resolve` в `resources/read` недостаточно.

## Основание и границы исследования

| Поле | Значение |
|---|---|
| Дата фиксации | 2026-10-18, 15:03:27 UTC |
| Роль | `mcp-worker`, `code-investigation` |
| Assignment | `pf121-oop-mcp-20261018-current-mcp-descriptions-tool-extension-seams-and` |
| Run | `garage-pf121-oop-mcp-20261018-current-mcp-descriptions-tool-extension-se` |
| Context | `pf121-oop-mcp-20261018-current-mcp-descriptions-tool-extension-seams-and-capsule` |
| Стадия | `investigation` |
| HEAD при исследовании | `2f027b9ff56019b96e17280dfe7e50bc7f5a43bc` |

Использованы переданные inline Python guidance, MCP brief и team brief, текущие исходники и документация проекта. Сначала изучались локальные документы; спорные положения MCP затем сверялись с официальной спецификацией.

Новый Work не создавался, контекст не перестраивался, PF MCP не вызывался. Вложенные агенты, серверы, установка, обновление и полные наборы проверок не запускались. Файлы не записывались.

## 1. Установленные факты

### 1.1. Текущая поверхность MCP

Основная реализация находится в `tools/pf_runtime/mcp_server.py`:

- `main` обслуживает stdio;
- `_respond` проверяет JSON-RPC envelope и схемы аргументов;
- `respond_valid` реализует протокольные методы;
- `_tool_result` связывает запрос с проектом, сессией и прикладными сервисами;
- `TOOLS`, `tool_schema`, `tool_annotations` формируют каталог.

Текущий каталог содержит **31 инструмент**, из которых **13** входят в `MUTATING_TOOLS`.

| Группа | Инструменты |
|---|---|
| Проект | `pf.context`, `pf.project_state`, `pf.project_initialization.status`, `.initialize`, `.repair` |
| Work | `pf.work_state`, `pf.work.state`, `pf.work.start`, `pf.work.transition` |
| Продолжение и отмена | `pf.continuation.create`, `.status`, `.resume`, `pf.work.cancel` |
| Ресурсная навигация | `pf.search`, `pf.resolve`, `pf.work.search`, `pf.work.resolve` |
| Workplace и сессия | `pf.workplace_state`, `pf.session_context`, `pf.session_chat`, `pf.session_activity` |
| Каталог операций | `pf.actions.list`, `pf.actions.describe` |
| Драйверы | `pf.runtime_driver.list`, `.describe` |
| Воркеры | `pf.worker.prepare`, `.start`, `.status`, `.collect` |
| Запись в Ledger | `pf.session.heartbeat`, `pf.chat.record` |

`respond_valid` объявляет `protocolVersion: 2024-11-05` и только `capabilities: {"tools": {}}`. Реализованы `initialize`, `notifications/initialized`, `tools/list`, `tools/call`. Методы `resources/list`, `resources/templates/list`, `resources/read`, `prompts/list`, `prompts/get` отсутствуют и возвращают `-32601`.

Результат инструмента передаётся как JSON внутри текстового элемента `content`. Текущая реализация не выдаёт embedded resources или отдельный структурированный результат.

Эти выводы относятся к исследованным исходникам. Поведение подключённого или установленного MCP-процесса не проверялось.

### 1.2. Уже существующие границы ответственности

| Файл / символ | Фактическая ответственность |
|---|---|
| `tools/pf_runtime/action_tools.py::ActionToolService` | Ограниченные адаптеры native actions с проверками схемы, `apply`, Work и сессии |
| `ActionToolDependencies` | Явно переданные зависимости адаптера |
| `NativeActionGateway.call` | Вызов CLI application callable без shell и subprocess CLI |
| `tools/pf_runtime/action_catalog.py::mcp_descriptors` | Получение описаний из фактического MCP-каталога |
| `src/processforge_core/operations/catalogue.py::ActionCatalog` | Работа с данными каталога без транспорта и чтения проекта |
| `ActionDescriptor`, `WorkFacts` | Неизменяемые описания и ограниченная проекция фактов Work |
| `src/processforge_core/resources/access.py` | Проектные search/resolve через узкие read ports |
| `src/processforge_core/work/resources.py::WorkResourceService` | Work-scoped search/resolve |
| `work/resource_context.py::WorkResourceContextReadService` | Проверка точной идентичности, capsule и закреплённых ресурсов |
| `work/material_read.py::WorkMaterialReadService` | Проверка текущего доступа, метаданных и материала |
| `work/resource_material.py::capture_material` | Ограниченное чтение и fingerprint материала; самостоятельно доступ не предоставляет |
| `src/processforge_core/composition.py` | Сборка существующих сервисов |

Основа для дальнейшего разделения уже есть. Новый контейнер зависимостей или общий механизм плагинов для исследованного среза не требуется.

## 2. Конкретные неточности описаний

Предлагаемые строки ниже сохраняют английский язык текущего каталога. Это **предложения**, а не внесённые изменения.

| Инструмент | Факт и проблема | Предлагаемое описание |
|---|---|---|
| `pf.work_state` | Назван compatibility alias, но возвращает `{project, work, context, session}` через project context. Не принимает `run_id`, `assignment_id`, `context_id`. Это другой контракт, чем `pf.work.state`. | `Read the legacy project-context Work projection. For exact Run/Assignment/context selection and current stage obligations, use pf.work.state.` |
| `pf.work.state` | Описание не объясняет селекторы. `_tool_result` передаёт их в execution service; без них применяется существующий механизм выбора Work. | `Read governed Work state, stage obligations and context validation. Supply exact run_id, assignment_id and context_id to inspect a specific Work; discovery is not permission to act.` |
| `pf.work.start` | «Start or continue» не объясняет условия продолжения. `_start_locked` ищет совпадающую objective, может вернуть `continue_existing`, а историческое совпадение блокирует отдельным результатом. | `Create governed Work for an objective or return matching active Work. Process ambiguity returns process_choice_required; continue a selected handoff through pf.continuation.resume.` |
| `pf.work.transition` | Не описаны закреплённый процесс и запрет выбора следующей стадии вызывающей стороной. | `Submit an outcome and evidence for the selected Work. The pinned process chooses the next stage or completion; next_stage is not an input.` |
| `pf.resolve` | Возвращает проектную навигацию, а не тело документа и не разрешение Work. Возможен приватный `local_root`. | `Resolve selected project-resource navigation from a fresh project snapshot. Returns metadata and possibly a private runtime location, not document contents or Work authorization.` |
| `pf.search` | «Before using broader search» может читаться как обещание fallback. Фактически общего или web-поиска нет; при missing/stale index возможно обслуживание локального индекса. | `Search the fresh project-authorized local index without filesystem-wide or web fallback. May refresh a missing or stale derived index; returned local paths are private runtime navigation.` |
| `pf.work.resolve` | «Resolve a verified resource» не сообщает, что тело документа не возвращается. Различаются `metadata_only` и `verified_declared_material`. | `Verify and resolve one resource for exact Work selectors under pinned, current and stage access. Returns navigation and provenance, not document contents; metadata_only does not authorize body reads.` |
| `pf.work.search` | Не объяснено отличие от проектного индекса и отсутствие полного тела в результатах. | `Search bounded material verified for exact Work selectors under pinned, current and stage access. Returns matching document metadata and provenance, not full document bodies.` |
| `pf.project_initialization.repair` | Описание ограничено deterministic PF state / agent entry, но схема и `repair_project` также допускают `install_codex_hooks`. | `With apply: true and an existing Ledger-bound project, run the selected repair_action. install_codex_hooks changes host integration and requires explicit operator authorization.` |
| `pf.workplace_state` | Не обозначена обязательность Ledger session, проверяемая перед этим маршрутом. | `Read derived workplace Ledger state through an existing Ledger-bound session.` |

Для `pf.context` полезно дополнить описание тем, что это начальная проекция; точные обязательства выбранного Work читаются через `pf.work.state`.

`pf.worker.status` уже описан достаточно точно: явно сказано, что наблюдение может изменять runtime records и собирать завершённый output. Он обоснованно не объявлен read-only. Описания `pf.actions.*` также правильно отделяют поддержку операции от разрешения её выполнить.

Не следует «исправлять алиас» перенаправлением `pf.work_state` на новый payload: это изменит выпущенный контракт. Исправлению подлежат описание и соответствующее утверждение в `docs/concepts/runtime-mcp.md`.

### 2.1. Недостаток описаний аргументов

Изолированная проверка каталога обнаружила **0 описаний верхнеуровневых свойств** в `inputSchema`.

Наиболее полезные дополнения:

- `project_root`: когда обязателен и как соотносится с привязанной сессией;
- Work selectors: использовать возвращённые PF значения, без самостоятельного выбора первого или последнего Work;
- `resource_id`: идентификатор ресурса, не путь;
- `process_id`: при неоднозначности выбирать только из предложенных кандидатов;
- `evidence`: сохранить текущие строковую и объектную формы;
- `apply`: точное JSON boolean; для action tools `false` не означает preview;
- `driver`: зарегистрированный ID, не путь к manifest или executable.

Добавление описаний не должно менять requiredness, допустимые значения и границу между protocol error и прикладным blocked-результатом. Изменение метаданных следует отдельно отразить в catalogue/schema fingerprints.

### 2.2. Аннотации и физические эффекты

`tool_annotations("pf.search")` возвращает `readOnlyHint: true`. Однако:

1. `ResourceSearchService.search` проверяет состояние workplace index.
2. При `missing` или `stale` вызывает `maintenance_tick`.
3. Обслуживание может вызвать `build_index`, который записывает SQLite и выполняет commit.

Это подтверждённое расхождение между аннотацией и физическим поведением. Изменение классификации или порядка обслуживания требует отдельного решения; его нельзя незаметно включать в перенос функций между классами.

Сервер также выдаёт annotations, объявляя версию `2024-11-05`. Annotations описаны в более поздней редакции Tools. Это повод для отдельной проверки совместимости, но недостаточное основание объявлять текущий сервер неработоспособным или менять версию протокола в этом срезе. Аннотации не заменяют проверки доступа. [MCP Tools 2025-03-26](https://modelcontextprotocol.io/specification/2025-03-26/server/tools)

Фиксированный ответ версией `2024-11-05` сам по себе не доказывает нарушения negotiation: спецификация допускает ответ другой поддерживаемой сервером версией. [MCP Lifecycle 2024-11-05](https://modelcontextprotocol.io/specification/2024-11-05/basic/lifecycle)

## 3. Фактические границы доступа Work

### 3.1. Проектная навигация и Work — разные области

`pf.search` и `pf.resolve` работают в `project_context`. Они не принимают точную тройку Work selectors.

`pf.work.search` и `pf.work.resolve` требуют `run_id`, `assignment_id`, `context_id` и используют `WorkResourceService`.

`WorkResourceContextReadService.read` проверяет:

- соответствие Run, Assignment и принадлежность задания Run;
- каноническую ссылку на capsule и checksum её байтов;
- `context_id`, неизменяемость capsule и внутреннюю идентичность;
- process definition, fingerprint и совпадение закреплённых данных;
- snapshot identity;
- согласованность selected resource IDs и bindings;
- execution contract, если он присутствует, включая разрешённое действие `read`;
- текущую стадию и её `resource_subset`.

Отсутствующий `resource_subset` наследует закреплённый набор. Явный `[]` не предоставляет ресурсов. Нельзя добавлять новые ресурсы в старую capsule на основании расширившегося текущего доступа.

`WorkMaterialReadService.read` до чтения материала проверяет текущий доступ и metadata fingerprints всего запрошенного набора. Затем сверяет generation, material fingerprint, material kind и manifest с закреплёнными значениями.

Идентификаторы Work определяют объект обращения. Для будущего сетевого интерфейса они не должны становиться заменой аутентификации и проверки доступа вызывающего субъекта.

### 3.2. Metadata не предоставляет тело

`WorkMaterialReadService.read` возвращает навигационный объект с:

- portable reference;
- generation и fingerprints;
- manifest;
- provenance;
- приватным runtime `local_root`;
- признаком `metadata_only` либо `verified_declared_material`.

Для операции resolve используется `capture_material(..., include_content=False)`: тело не возвращается клиенту.

Для search содержимое fulltext-материала обрабатывается внутри запроса. `search_material` строит SQLite FTS в памяти и исключает поле `content` из возвращаемых совпадений.

`PreparedKnowledgeResourceReader.read` отдельно сохраняет эту границу: fulltext получает разрешённую runtime resolution, metadata — `status: metadata_only`.

Следовательно, наличие `local_root`, manifest или успешного resolve нельзя превращать в универсальное разрешение читать файлы каталога.

### 3.3. Действующие бюджеты

| Ограничение | Значение |
|---|---:|
| Ресурсов на запрос | 64 |
| Файлов суммарно | 2 048 |
| Исходного содержимого суммарно | 32 MiB |
| Посещённых записей | 20 000 |
| Файлов на ресурс | 256 |
| Содержимого на ресурс | 8 MiB |
| Размер файла | 1 000 000 байт |
| Сгенерированных поисковых документов | 2 048 |
| UTF-8 поисковых документов суммарно | 32 MiB |

Источник: `work/resource_material.py::DEFAULT_LIMITS`, `MaterialBudget` и `resources/local_search.py::MAX_FILE_BYTES`.

Превышение блокируется, а не маскируется как полный результат. Механизм использует containment, проверки ссылок, identity открытого файла и content hashes; mtime не служит единственным доказательством неизменности. Прямой вызов `capture_material` не является проверкой полномочий.

## 4. Возможность MCP resources и prompts

### 4.1. Что поддерживает протокол

Resources можно добавить без смены объявленной редакции MCP: версия `2024-11-05` предусматривает capability `resources`, `resources/list`, `resources/read` и URI templates. Подписки и уведомления об изменении списка опциональны. Допускается собственная URI scheme. [MCP Resources 2024-11-05](https://modelcontextprotocol.io/specification/2024-11-05/server/resources)

Prompts — отдельная capability с `prompts/list` и `prompts/get`; наличие каталога `prompts/` в репозитории не означает её поддержку сервером. [MCP Prompts 2024-11-05](https://modelcontextprotocol.io/specification/2024-11-05/server/prompts)

### 4.2. Подходящие кандидаты

**Предложения, в порядке целесообразности:**

| Кандидат | Оценка |
|---|---|
| Ограниченная проекция каталога действий | Наименьший новый риск: данные уже формируются существующим каталогом |
| Безопасная проекция точного Work state | Полезна интерфейсу; нужна фильтрация приватных полей и повторная проверка доступа |
| Дескриптор разрешённого Work resource | Реализуем без выдачи тела; нельзя переносить `local_root` в публичную проекцию |
| Один явно разрешённый fulltext-документ | Практическая польза есть, но нужен отдельный body-read контракт |
| Произвольный файл проекта | Не включать в минимальный срез: требует полноценной проверки файловой области |
| Raw capsule, transcript, worker output | Не выдавать целиком: возможны приватные пути, содержимое и иные чувствительные данные |
| Вся база знаний workplace | Необоснованное расширение доступа и объёма; не предлагать |

Существенная потребность в дополнительном чтении существует у клиента без прямого доступа к файловой системе: search/resolve находят и проверяют материал, но не доставляют текст документа. Это обоснование узкого чтения документа, а не общей выгрузки знаний.

### 4.3. Минимальная архитектура URI/list/read

**Предложение, требующее согласования перед реализацией.**

Использовать логические URI, например:

```text
pf://catalog/actions
pf://projects/{project_handle}/runs/{run_id}/assignments/{assignment_id}/contexts/{context_id}/resources/{resource_id}/documents/{document_id}
```

`project_handle` и `document_id` — логические идентификаторы. URI не должен содержать абсолютный путь, credentials или давать возможность передать произвольный filesystem root.

Минимальный адаптер должен обеспечивать:

1. **Явный выбор проекта.** Host передаёт разрешённое соответствие project handle локальному проекту. Сам handle не предоставляет доступ.
2. **Отсутствие неявного выбора Work.** Не использовать последний `pf.context`, последний tool call, первый или самый новый Work.
3. **Ограниченный list.** Возвращать только доступные дескрипторы с pagination; без полной индексации и тел документов.
4. **Повторную проверку read.** URI, membership, текущий доступ, стадия, checksum capsule и material fingerprints проверяются при каждом чтении.
5. **Единый прикладной сервис.** MCP, CLI и будущий web вызывают одну реализацию доступа и чтения.
6. **Раздельные ошибки.** Невалидный URI, недоступный ресурс, изменившийся материал и превышение бюджета должны иметь стабильные причины без приватных путей.

Стандартный `resources/list` принимает cursor, но не PF-параметры `project_root` и Work selectors. Поэтому при отсутствии разрешённой project binding список Work resources должен быть пустым. Нельзя обходить это скрытым выбором проекта. Общие URI templates допустимы без перечисления приватных объектов. [MCP Resources 2024-11-05](https://modelcontextprotocol.io/specification/2024-11-05/server/resources)

Для клиентов без сессии существующие инструменты с явным `project_root` сохраняют значение. Не следует делать Ledger обязательным для файлового режима ради удобства resource listing.

### 4.4. Дополнительные требования к чтению тела

Новый сервис должен отдельно подтверждать body-read permission. Политики индексирования и `verified_declared_material` нельзя молча переопределить как универсальное разрешение доставки полного текста.

Необходимые проверки:

- выбранный документ входит в закреплённый manifest;
- metadata/none ресурсы не предоставляют тело;
- выполняются текущие ограничения Work и, при worker-вызове, применимые prepared grants;
- для файлов проекта действует `scope_allows`, включая `forbidden_files`;
- ресурсные grants не превращаются в разрешение читать соседние файлы;
- запрещены traversal, абсолютные пути, escape через ссылки и подмена файла;
- выдаётся проверенный документ, а не строка поискового индекса с добавленным metadata summary;
- listing, URI и кеш не обходят отзыв доступа.

`WorkResourceService` сейчас проверяет закреплённые Work resources. Отдельный prepared grants envelope не является входным параметром его `read`. Для worker-facing body API это различие необходимо явно разрешить в дизайне.

### 4.5. Актуальность, объём и приватность

Для первого resource-среза предлагается:

- только текст и небольшие JSON-проекции;
- отдельный лимит сериализованного ответа, например 256 KiB;
- лимит текста одного документа, например 64 KiB;
- ошибка превышения вместо молчаливого обрезания;
- отсутствие subscriptions, watchers и постоянного кеша тел;
- provenance с context checksum и fingerprints;
- повторная проверка текущего доступа независимо от совпадения content hash.

Указанные размеры — новые предлагаемые лимиты доставки, а не действующие бюджеты материала. Стандартный `resources/read` не задаёт PF-диапазонное чтение; добавлять собственное разбиение до появления потребности не требуется.

Raw `local_root` из Work resolve и `local_path` из проектного search являются приватной runtime-навигацией. Они не подходят для общедоступного URI или web DTO.

Дополнительный канал риска виден в `ActionToolService._failure` и `execute`: `native_diagnostic` и `native_summary` получают ограниченные по длине фрагменты native output без общей фильтрации приватных путей. Это наблюдение по исходникам, а не подтверждённая фактическая утечка. Перед переиспользованием таких ответов в web нужна явная политика представления.

### 4.6. Prompts

В ближайший срез добавлять prompts не рекомендуется. Текущие startup, prepared input и process stages уже задают инструкции исполнения; второй каталог создаст обязанность поддерживать их согласованность.

Будущий prompt может помогать пользователю сформулировать objective или подготовить проверку. Получение prompt не должно создавать Work, выбирать процесс, расширять grants или автоматически загружать знания.

## 5. Границы сервисов для stdio, файлового режима и web

### 5.1. Каталог MCP

**Предложение:** вынести определения инструментов из `mcp_server.py` в отдельный адаптерный модуль с неизменяемыми описаниями схем и аннотаций.

Один источник должен обслуживать:

- `tools/list`;
- `tool_schema` и `tool_annotations`;
- `action_catalog.mcp_descriptors`.

Не следует вводить второй ручной список операций. `ActionDescriptor` уже предоставляет полезную модель с canonical JSON контракта; MCP-specific registry и обработчики при этом могут оставаться в адаптерном слое.

Сохранить различие порядка: текущий `tools/list` следует порядку registry, а `mcp_descriptors` сортирует имена.

### 5.2. Привязка запроса

**Предложение:** выделить существующее разрешение project/session в небольшой сервис с явно переданными зависимостями.

Его результат должен содержать проверенную идентичность проекта и сессии. Work selectors остаются явными данными запроса. Это позволит переиспользовать правила, не смешивая stdio flags, Ledger lookup и доменные операции.

При переносе сохранить действующие различия проверок. Например, action tools используют strict canonical project binding; нельзя случайно заменить её сравнением только project IDs.

### 5.3. Прикладные операции

Существующие `ProcessExecutionService`, `ContinuationService`, resource services и initialization service должны сохранять бизнес-правила. Транспорт отвечает за envelope, codec, схему и представление ошибок.

Для нового чтения документа уместен отдельный `WorkDocumentReadService` с явными зависимостями проверки доступа и файлового чтения. Он не должен зависеть от JSON-RPC или стартовать Runtime.

CLI сможет вызывать тот же сервис и печатать результат; web — применять сетевую аутентификацию, выбирать разрешённый проект и возвращать безопасную проекцию.

### 5.4. Native action gateway

`NativeActionGateway` уже исключает shell execution. Для последовательного stdio это полезный существующий механизм.

Однако `redirect_stdout`/`redirect_stderr` и разбор CLI text output не следует считать готовым сервисным API для параллельного web-сервера. Здесь целесообразно постепенно выделять структурированные результаты отдельных прикладных операций. Создавать универсальный command executor или добавлять классы вокруг каждой CLI-функции не требуется.

## 6. Предлагаемый следующий согласованный срез

### Срез A: точность каталога и выделение метаданных

Рекомендуемый первый шаг:

1. Уточнить описания из раздела 2 и ключевые аргументы.
2. Исправить документационное утверждение об эквивалентности `pf.work_state`.
3. Выделить каталог MCP без изменения маршрутизации и поведения.
4. Сохранить схемы, порядок, payloads, stable error codes и текущие проверки.
5. Зафиксировать отдельно решение по эффектам `pf.search`.

Основные существующие точки изменения:

- `tools/pf_runtime/mcp_server.py`;
- `tools/pf_runtime/action_tools.py`;
- `tools/pf_runtime/action_catalog.py`;
- `docs/concepts/runtime-mcp.md`;
- `docs/concepts/action-discovery.md`.

Resources/prompts, новую авторизацию, запуск инфраструктуры и смену протокола в этот срез не включать.

### Срез B: один документ через общий сервис

Только после согласования body-read policy:

- один документ из явно разрешённого Work resource;
- точные Work selectors;
- явный body denial для metadata;
- bounded text и provenance;
- общий сервис для CLI/MCP;
- без произвольного filesystem read.

Дальнейшие URI/list/read handlers должны быть адаптерами этого сервиса, а не отдельной реализацией доступа.

### Узкие проверки для следующих срезов

| Область | Проверка |
|---|---|
| Каталог | Сохраняются 31 имя, порядок `tools/list`, схемы и аннотации, кроме отдельно согласованных изменений |
| Старый маршрут | `pf.work_state` сохраняет прежний payload и отказ на Work selectors |
| Схемы | Unknown fields, boolean вместо integer, string/array limits блокируются до dispatch |
| Привязка | Session mismatch и canonical project mismatch отклоняются до native operation |
| Work | Точные selectors, checksum mismatch, stage subset `[]`, revoked resource и legacy bindings |
| Документ | Metadata body denied; чужой document ID, traversal, ссылка наружу и смена hash блокируются |
| Объём | Превышение body/response budget не выдаётся как полный документ |
| Приватность | URI, cursor, публичные ответы и ошибки не содержат private roots или native output |
| Транспорт | UTF-8, JSON-RPC errors и отсутствие ответа notifications сохраняются |
| Режимы | Один сервис даёт согласованный результат через CLI и MCP без обязательного app-server |

Существующие узкие основы: `tools/smoke_mcp_action_tools.py`, `smoke_mcp_jsonrpc_validation.py`, `smoke_mcp_codex_contract.py`, `smoke_work_resource_binding.py`, `smoke_resource_search_snapshot_composition.py`.

Проверки с созданием Work и изменением fixtures следует выполнять только в разрешённой изолированной области следующего задания.

## 7. Выполненная проверка и ограничения уверенности

Проведена изолированная проверка функций из текущих исходников через AST. Продуктовые модули не импортировались; bootstrap и business dispatch не выполнялись. Вызов `tool_result` был запрещён тестовым stub. Python запускался с `-B`.

Результат — **PASS**:

- каталог содержит 31 инструмент;
- mutating-набор содержит 13 инструментов;
- initialize возвращает `2024-11-05` и только tools capability;
- пять проверенных resources/prompts методов возвращают `-32601`;
- legacy state schema отклоняет Work selectors, новая принимает;
- `pf.worker.status` не отмечен read-only;
- `pf.worker.start` отмечен open-world;
- integer schema не принимает boolean;
- верхнеуровневые свойства схем не имеют descriptions.

Проверка не подтверждает installed-host parity, поведение действующих воркеров или runtime-инфраструктуры. Полные smoke suites не запускались.

Для воспроизводимости рассчитан fingerprint девяти основных исследованных файлов:

```text
sha256:67505005c1b7b6845cdea9ad1efd51dec57859c18f35e1defba8ea23df705bc9
```

Набор: `mcp_server.py`, `action_tools.py`, `action_catalog.py`, `operations/catalogue.py`, `resources/access.py`, `work/resources.py`, `work/resource_context.py`, `work/material_read.py`, `work/resource_material.py`. Fingerprint рассчитан по отсортированному списку относительных путей и SHA-256 байтов каждого файла.

Serena использована для поиска и чтения символов. Первый поиск отвечал с задержкой; для начального обзора имён применён ограниченный shell-поиск. Он встретил отказ доступа к постороннему временному каталогу; ограничение не обходилось. Необходимые текущие исходники были доступны. Архивные копии и старый подключённый MCP не использовались как доказательство поведения.

### Журнал исследования

Время фиксации записей: **2026-10-18 15:03:27 UTC**.

| Роль | Действие и исследованные файлы | Статус / остаточные вопросы |
|---|---|---|
| `mcp-worker` | Сопоставлены inline inputs и ограничения | Завершено; запись файлов и делегирование не выполнялись |
| `mcp-worker` | Изучены `runtime-mcp.md`, `work-resources.md`, `resource-privacy.md`, `action-discovery.md` | Завершено |
| `mcp-worker` | Проверены MCP routes, schemas, annotations, action adapters и catalogue | Завершено; найдены конкретные неточности описаний |
| `mcp-worker` | Прослежены resource context, material verification и prepared knowledge grants | Завершено; будущий body API требует отдельного контракта |
| `mcp-worker` | Сверены официальные MCP Resources, Prompts, Tools и Lifecycle | Завершено; протокол менять в первом срезе не предложено |
| `mcp-worker` | Выполнена изолированная проверка каталога и protocol handlers | PASS; без business dispatch |
| `mcp-worker` | Подготовлены границы сервисов, расширения и узкие проверки | Исследование завершено; реализация требует следующего согласованного среза |