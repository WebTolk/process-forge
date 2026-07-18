# Agent Prompts

Эти snippets можно передавать ИИ-агенту. Они задают правильную модель:
ProcessForge установлен как инструмент, workplace находится на машинном уровне,
а проектные инструкции лежат в `.pf/START_AGENT_HERE.md`.

## Использование ProcessForge с агентскими окружениями

Не копируйте весь репозиторий ProcessForge в `.codex`, `.claude`, `.agents`
или похожие папки конфигурации агентов.

Установите ProcessForge один раз как инструмент, инициализируйте workplace и
добавьте короткую инструкцию в конфигурацию агента: где установлен ProcessForge
и что проектные инструкции находятся в `.pf/START_AGENT_HERE.md`.

## Prompt: initialize workplace

```text
Ты настраиваешь ProcessForge на этой машине.

Используй ProcessForge как файловый инструмент для рабочих процессов.
Инициализируй новое рабочее место, запусти doctor-workplace и создай краткий отчёт о настройке.

Используй:

python <processforge-root>/bin/pf.py workplace-init --workplace <workplace-path> --apply

Пока не меняй конкретные проекты.
Не создавай .pf внутри проекта.
После настройки покажи путь к workplace, результат doctor и следующую команду для подключения проекта.
```

## Prompt: onboard project

```text
Ты подключаешь этот проект к ProcessForge.

Сначала изучи структуру проекта. Затем подключи его к существующему ProcessForge workplace.

Используй:

python <processforge-root>/bin/pf.py project-onboard --project-root . --workplace <workplace-path> --type <project-type> --apply

После подключения:
1. Прочитай .pf/START_AGENT_HERE.md.
2. Запусти doctor-project.
3. Кратко опиши project snapshot.
4. Предложи первый run/task план.
```

## Prompt: create reusable template

```text
Создай новый переиспользуемый шаблон ProcessForge.

Используй flow создания шаблонов. Предложи id шаблона, название, тип, входные параметры, выходные файлы и примеры. Затем создай шаблон и запусти template-doctor.

Используй:

python <processforge-root>/bin/pf.py template-create --workplace <workplace-path> --id <template-id> --title "<title>" --apply
python <processforge-root>/bin/pf.py template-doctor --workplace <workplace-path> --template <template-id>

Покажи созданные файлы и объясни, как использовать шаблон в проекте.
```

## Prompt: create knowledge package

```text
Создай новый пакет знаний ProcessForge.

Спроси, какой источник знаний нужно добавить: URL, локальную папку, markdown-файлы, заметки или план зеркалирования документации.
Создай пакет в выбранном package root, добавь начальный resource index и запусти knowledge-package-doctor.

Используй:

python <processforge-root>/bin/pf.py knowledge-package-create --workplace <workplace-path> --id <package-id> --title "<title>" --package-root global --apply
python <processforge-root>/bin/pf.py knowledge-package-doctor --workplace <workplace-path> --package <package-id>

Не записывай приватные абсолютные пути в публичные файлы. Используй path_ref или private resource registry, если нужно.
```

## Prompt: create platform contract

```text
Создай новый контракт платформы ProcessForge.

Спроси о project type hints, обязательных capabilities, рекомендуемых пакетах знаний, шаблонах, tools, MCP-серверах и процессах по умолчанию.
Создай platform contract и запусти platform-contract-doctor.

Используй:

python <processforge-root>/bin/pf.py platform-create --workplace <workplace-path> --id <platform-id> --title "<title>" --apply
python <processforge-root>/bin/pf.py platform-contract-doctor --workplace <workplace-path> --platform <platform-id>

Не копируй пакеты и шаблоны внутрь platform contract. Ссылайся на них по id.
```

## Prompt: create custom process

```text
Создай новый процесс ProcessForge через process authoring workflow.

Не пиши YAML вручную первым шагом. Начни authoring session, предложи значения по умолчанию, спроси меня о стадиях, ролях, артефактах, gates, нужных знаниях, tools и цикле task/iteration. Поддерживай answers.yaml и draft.process.yaml в актуальном состоянии.

Используй:

python .pf/runtime/bin/pf.py process-authoring-start --project-root . --id <process-id> --title "<title>" --scope project --kind operational --apply
python .pf/runtime/bin/pf.py process-authoring-review --project-root . --id <process-id>
python .pf/runtime/bin/pf.py process-authoring-apply --project-root . --id <process-id> --apply
python .pf/runtime/bin/pf.py process-doctor --project-root . --process <process-id>

Проверь, что новый процесс можно использовать через run-create.
```

## Prompt: create task batch run

```text
Создай ProcessForge run для этой рабочей сессии.

Используй task-batch workflow. Создай run, разбей работу на задачи и для каждой задачи фиксируй итерации work/debug/fix/review. В конце создай run summary и handoff.

Используй:

python .pf/runtime/bin/pf.py run-create --project-root . --id <run-id> --title "<title>" --process task-batch-execution --apply
python .pf/runtime/bin/pf.py task-create --project-root . --run <run-id> --id <task-id> --title "<task title>" --process <process-id> --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind work --summary "..." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind debug --summary "..." --apply
python .pf/runtime/bin/pf.py task-complete --project-root . --task <task-id> --summary "..." --apply
python .pf/runtime/bin/pf.py run-summary --project-root . --run <run-id> --apply
python .pf/runtime/bin/pf.py run-doctor --project-root . --run <run-id>
```
