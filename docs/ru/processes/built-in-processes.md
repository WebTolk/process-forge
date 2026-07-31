# Этапы встроенных процессов

ProcessForge поставляется со встроенными core-процессами в `processes/core/`.
Эти процессы являются файловыми workflow: YAML-описание процесса остаётся
авторитетным контрактом, а эта страница даёт человекочитаемую карту этапов.

Используйте эту страницу, чтобы выбрать процесс перед запуском работы. Для
точного текущего контракта запускайте:

```bash
python bin/pf.py process-describe --project-root . --process <process-id>
```

## Процесс разработки

Для обычной продуктовой или кодовой работы первым выбирайте
`task-batch-execution`. Это базовый процесс разработки для режима гаража
`1-1-1-1`: один оператор, один основной агент, один проект и один активный run.

Этапы:

1. `run-intake`: создать run или изучить уже активный run.
2. `task-planning`: создать задачи на основе assignments и привязать их к run.
3. `task-execution-loop`: выполнять работу записанными итерациями: анализ,
   реализация, отладка, тестирование, review, исследование, handoff или заметки.
4. `task-result-fixation`: закрыть каждую задачу кратким итогом или
   результатным артефактом.
5. `run-review`: выполнить `run-doctor` и `task-doctor` перед завершением.
6. `run-summary`: собрать результаты задач в итоговый summary и handoff.

Этот процесс намеренно практичный. Он не требует Director Office, leases,
внешних workers или фонового демона. Используйте его для обычных задач
разработки, подготовки релиза, документации, исправления ошибок и фич, которые
один основной агент может безопасно координировать.

Если работу нужно разделить между независимыми агентскими сессиями, используйте
`multi-agent-task-orchestration`. Если workers должны запускаться как shell-agent
процессы через runtime drivers, используйте
`orchestrator-shell-agents-supervision`.

## Как выбрать процесс

| Задача | С чего начать |
|---|---|
| Работа над проектом, фичей, багом, релизом или документацией | `task-batch-execution` |
| Подключить существующий репозиторий к ProcessForge | `project-onboarding` |
| Инициализировать новый project flow и изучить специфику проекта | `project-initialization` |
| Подготовить machine-level workplace | `guided-workplace-setup` или `workplace-initialization` |
| Разделить работу между независимыми агентами | `multi-agent-task-orchestration` |
| Запустить shell workers из orchestrator plan | `orchestrator-shell-agents-supervision` |
| Создать новый process definition | `process-authoring` |
| Обновить версию процесса | `process-version-upgrade` |
| Создать знания, шаблоны, инструменты, MCP или платформенные ресурсы | соответствующий authoring/register process |

## Справочник этапов

| Процесс | Назначение | Этапы |
|---|---|---|
| `agent-director-supervision` | Координация organized-проектов через handoffs, availability, leases, target runs и continuation capsules. | `inspect` -> `assign` -> `wait-or-return` |
| `authoring-parity-audit` | Проверка существующих процессов и ресурсов на воспроизводимость через authoring workflows. | `intake` -> `discover-existing-processes` -> `import-authoring-answers` -> `generate-candidates` -> `semantic-compare` -> `doctor-candidates` -> `resource-parity-checks` -> `report-findings` -> `handoff` |
| `context-resolution` | Сбор источников в context index, правила, conflict report и assignment context packages. | `source-discovery` -> `rule-classification` -> `cascade-merge` -> `conflict-detection` -> `context-index-generation` -> `resolved-rules-generation` -> `fingerprint-recording` -> `ecp-capsule-generation` |
| `guided-workplace-setup` | Пошаговая настройка workplace с участием человека: ответы, proposal и apply. | `intake` -> `dialogue` -> `review` -> `apply` |
| `knowledge-package-authoring` | Создание workplace knowledge package через authoritative package roots. | `intake` -> `select-package-root` -> `create-package-structure` -> `write-package-manifest` -> `create-resource-index` -> `add-initial-resources` -> `run-package-doctor` -> `handoff` |
| `knowledge-package-improvement` | Предложение, проверка и интеграция повторно используемого process knowledge. | `propose` -> `assess` -> `integrate` |
| `knowledge-package-update` | Обновление knowledge package через inspection, proposal, update и compatibility checks. | `current-package-inspection` -> `change-proposal` -> `resource-update` |
| `knowledge-resource-add` | Добавление knowledge resource через proposal, classification, index refresh, validation и review. | `intake` -> `target-resolution` -> `package-index-update` -> `validation` |
| `mcp-register` | Регистрация MCP capability provider без сохранения секретов. | `intake` -> `registry-update` |
| `multi-agent-task-orchestration` | Разбиение работы на ограниченные worker assignments для нескольких agent sessions. | `plan` -> `assign` -> `worker-execution` -> `integration-review` |
| `orchestrator-shell-agents-supervision` | Запуск и надзор shell-agent worker sessions через runtime drivers. | `plan` -> `launch` -> `collect` |
| `platform-contract-authoring` | Создание platform contract, который связывает project type hints с ресурсами и процессами. | `intake` -> `select-platform-root` -> `create-platform-structure` -> `write-platform-contract` -> `link-capabilities` -> `link-knowledge-packages` -> `link-templates` -> `link-tools-mcp` -> `run-platform-doctor` -> `handoff` |
| `platform-contract-install` | Создание или обновление platform contract с capabilities и ресурсами. | `platform-definition` -> `contract-creation` |
| `process-authoring` | Создание, review, apply и validation нового ProcessForge process definition. | `intake` -> `draft-process` -> `logic-review` -> `apply-process` -> `process-doctor` -> `handoff` |
| `process-supervisor` | Подготовка, запуск, наблюдение, проверка и сбор состояния external runtime worker. | `prepare` -> `start` -> `collect` |
| `process-version-upgrade` | Оценка и безопасное выполнение upgrade между версиями процесса. | `compare` -> `decide` |
| `processforge-update-check` | Проверка update index связанного ProcessForge distribution и оценка влияния на проект. | `discover` -> `assess` |
| `project-initialization` | Подключение проекта к ProcessForge и настроенному workplace layer. | `intake` -> `workplace-resolution` -> `repository-scan` -> `project-classification` -> `global-resource-matching` -> `project-specificity-extraction` -> `proposal` -> `review` -> `apply` -> `doctor` |
| `project-onboarding` | Подключение проекта к существующему ProcessForge workplace без пересоздания workplace. | `intake` -> `create-project-flow` -> `detect-project` -> `snapshot` -> `first-assignment` -> `validate` -> `handoff` |
| `reusable-template-authoring` | Создание, регистрация, validation и handoff reusable workplace template. | `intake` -> `select-template-root` -> `create-template-structure` -> `write-manifest` -> `write-example-files` -> `register-template` -> `run-template-doctor` -> `handoff` |
| `runtime-driver-registry` | Управление neutral runtime driver manifests и registry entries. | `inventory` -> `validate` |
| `session-bootstrap` | Старт или проверка primary agent session и разрешение текущего project state. | `intake` -> `mode-detection` -> `flow-location` -> `workplace-resolution` -> `context-freshness-check` -> `status-scan` -> `session-report` |
| `task-batch-execution` | Последовательное выполнение проектной работы внутри одного primary agent run. | `run-intake` -> `task-planning` -> `task-execution-loop` -> `task-result-fixation` -> `run-review` -> `run-summary` |
| `template-add` | Добавление простой reusable template folder и optional registry entry. | `intake` -> `template-folder-creation` |
| `tool-register` | Регистрация workplace tool capability provider. | `intake` -> `registry-update` |
| `workplace-initialization` | Инициализация или обновление machine-local workplace layer. | `intake` -> `device-discovery` -> `terms-setup` -> `registry-setup` -> `tool-discovery` -> `mcp-discovery` -> `proposal` -> `review` -> `apply` -> `doctor` |

## Проверка

Перед изменением встроенного процесса запускайте:

```bash
python bin/pf.py process-doctor --project-root . --process <process-id> --contract-only
python bin/pf.py builtin-process-catalog-doctor --root . --public
```

Перед публикацией релиза, где менялись процессы или эта документация,
запускайте обычные release gates из release checklist.
