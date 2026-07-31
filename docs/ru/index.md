# Документация ProcessForge

**Документация на английском:** [../index.md](../index.md)

![Схема рабочего места ProcessForge](../assets/processforge-architecture.svg)

ProcessForge — файловая среда для управляемой работы человека и ИИ-агентов над
проектами. Начните с установки, затем создайте workplace, подготовьте общие
ресурсы, подключите проект и передайте агенту `.pf/START_AGENT_HERE.md`.

Верхний уровень модели: workplace - это машина, где работают человек и агенты;
ProcessForge установлен один раз как инструмент; общие ресурсы живут в
workplace; каждый репозиторий хранит только проектный слой `.pf/`.

Обязательный порядок инициализации: сначала workplace, затем ресурсы workplace,
затем подключение проекта. Для настройки новой машины с участием человека по
умолчанию используйте пошаговую настройку workplace. Полностью автоматический
путь используйте только когда оператор дал явные пути и решения.

## Для человека

- [Корневой README](../../README.ru.md)
- [Промпты быстрого старта](../../QUICKSTART.ru.md)
- [Установка](getting-started/installation.md)
- [Пошаговая настройка workplace](getting-started/guided-workplace-setup.md)
- [Порядок инициализации](getting-started/initialization-order.md)
- [Workplace vs project](concepts/workplace-vs-project.md)
- [Создание ресурсов](../getting-started/resource-authoring.md)
- [Подключение проекта](getting-started/project-onboarding.md)
- [Этапы встроенных процессов](processes/built-in-processes.md)

## Для ИИ-агентов

- [Командный справочник агента и промпты](getting-started/agent-prompts.md)
- [Промпт агента для пошаговой настройки workplace](../../prompts/guided-workplace-setup-agent.md)
- [Промпт агента для автоматической инициализации workplace](../../prompts/workplace-initialization-agent.md)
- [Промпт агента для подключения проекта](../../prompts/project-onboarding-agent.md)
- [Чек-лист релиза](../release-checklist.md)
- [Проверки](../validation/validation.md)

## Начало работы

- [Установка](getting-started/installation.md)
- [Первый запуск](getting-started/first-run.md)
- [Порядок инициализации](getting-started/initialization-order.md)
- [Инициализация workplace](getting-started/workplace-initialization.md)
- [Пошаговая настройка workplace](getting-started/guided-workplace-setup.md)
- [Подключение проекта](getting-started/project-onboarding.md)
- [Командный справочник агента и промпты](getting-started/agent-prompts.md)
- [Первый собственный процесс](getting-started/create-your-first-process.md)
- [Рабочий сценарий task batch](getting-started/task-batch-workflow.md)
- [Этапы встроенных процессов](processes/built-in-processes.md)
- [Multi-agent orchestration](getting-started/multi-agent-orchestration.md)
- [Runtime driver and supervisor](getting-started/runtime-driver-supervisor.md)

## Авторинг

- [Повторно используемые шаблоны](authoring/reusable-template-authoring.md)
- [Пакеты знаний](authoring/knowledge-package-authoring.md)
- [Платформенные контракты](authoring/platform-contract-authoring.md)
- [Создание процессов](authoring/process-authoring.md)
- [Паритет authoring](authoring/authoring-parity.md)
- [Пополнение существующих процессов](authoring/backfill-existing-processes.md)

## Концепции

- [Workplace vs project](concepts/workplace-vs-project.md)
- [Модель среды выполнения](concepts/runtime-model.md)
- [Модель агентской сессии](concepts/agent-session-model.md)
- [Режимы координации проекта](concepts/project-coordination-modes.md)
- [Runtime drivers](concepts/runtime-drivers.md)
- [Process supervisor](concepts/process-supervisor.md)
- [Граница Director, Ledger, Inspector и Worker](concepts/director-ledger-inspector-boundary.md)
- [Константы путей](concepts/path-constants.md)
- [Корни пакетов](concepts/package-roots.md)
- [Снимок проекта](concepts/project-snapshot.md)
- [Runs, tasks и iterations](concepts/runs-tasks-iterations.md)
- [Process definition, run, task, iteration](concepts/process-definition-run-task-iteration.md)
- [Multi-agent orchestration](concepts/multi-agent-orchestration.md)
- [Платформенные контракты](concepts/platform-contracts.md)
- [Наследование платформ](concepts/platform-inheritance.md)
- [Навигация по ресурсам знаний](concepts/knowledge-resource-navigation.md)
- [Hooks и events](concepts/hooks-events.md)
- [Semantic parity](concepts/semantic-parity.md)

## Порядок слоёв

1. Устройство workplace: компьютер, ноутбук, сервер или узел выполнения.
2. ProcessForge tool root: CLI, схемы, процессы, документация, шаблоны и
   проверки.
3. Общие ресурсы workplace: пакеты знаний, повторно используемые шаблоны,
   инструменты, MCP providers, platform contracts, корневые каталоги, реестры и
   данные среды выполнения.
4. Проектный слой `.pf/`: выбранные ресурсы, project context, назначения,
   запуски, задачи, итерации, артефакты, проверки, передачи и hooks.

Platform contracts являются композиционными манифестами. Они могут описывать
одну платформу или стек parent/child и подключать ресурсы, нужные конкретному
проекту. Process definitions остаются платформенно-независимой механикой
процесса.

## Релизы

- [Initial release notes](releases/initial-release.md)
- [Ограничения](known-limitations.md)
