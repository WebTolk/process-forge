# ProcessForge

**English documentation:** [README.md](README.md)

ProcessForge - файловый framework для управляемой работы человека и
ИИ-агентов над проектами. Он хранит definitions процессов, runs, tasks,
iterations, artifacts, reviews, handoffs, knowledge packages, templates, tools,
MCP registrations и platform contracts в версионируемых файлах.

Этот README написан для человека. Он начинается с модели рабочего места и даёт
готовые prompts для оператора. ИИ-агенты должны использовать command runbook в
[docs/ru/getting-started/agent-prompts.md](docs/ru/getting-started/agent-prompts.md);
там перечислены только команды и механики, подтверждённые текущей кодовой базой.

![Схема рабочего места ProcessForge](docs/assets/processforge-architecture.svg)

## Рабочая Модель

Рабочее место - это физическая или виртуальная машина, где работают человек и
ИИ-агенты: компьютер, ноутбук, сервер или runner host. ProcessForge
устанавливается один раз как инструмент этого рабочего места.

Workplace хранит глобальные машинные ресурсы: definitions процессов, knowledge
packages, reusable templates, tool registrations, MCP registrations, platform
contracts, roots, registries, cache, runtime events и logs.

Каждый проект хранит собственный слой `.pf/`. Проектный слой содержит project
context, выбранные глобальные ресурсы, assignments, runs, tasks, iterations,
artifacts, reviews, handoffs, hooks и private runtime files.

Атомарная единица выполнения - `1-1-1-1`: один человек-оператор, одна основная
агентская сессия, один проект и один активный process/run. В стандартном
single-agent flow primary agent сам выполняет работу, запускает CLI checks,
пишет artifacts и делает checkout; Worker и Inspector являются фазой
выполнения и проверками той же сессии, а не отдельными участниками. Agent
Ledger - это CLI/files, не отдельный агент. Director и Supervisor / Execution
Inspector нужны только для multi-agent, process-transition или external
runtime-worker сценариев. См.
[docs/ru/concepts/agent-session-model.md](docs/ru/concepts/agent-session-model.md).

Process definitions описывают механику процесса. Это YAML-конструкторы с
произвольным количеством stages, roles, artifacts, gates, capabilities, allowed
tools и hooks. Им не нужно называть конкретную implementation platform.

Platform contracts - композиционные сущности для конкретного проектного
контекста. Platform может быть одиночной или составной: parent плюс child.
Контракт подключает required/recommended стек knowledge packages, templates,
tools, MCP providers, capabilities, processes, coding standards, project type
hints и policy data. Ядро ProcessForge разрешает эти контракты из manifests; в
коде ядра нет hardcode конкретных продуктов, CMS, frameworks, marketplaces или
business domains.

## Порядок Инициализации

Для нового рабочего места используйте такой порядок:

1. Установить ProcessForge distribution.
2. Проверить ProcessForge distribution.
3. Инициализировать workplace.
4. Настроить path constants и roots.
5. Настроить knowledge roots, особенно локальные documentation roots.
6. Зарегистрировать tools и MCP servers.
7. Создать или импортировать knowledge packages.
8. Создать reusable templates.
9. Создать platform contracts из уже готовых ресурсов.
10. Подключить проекты к workplace.
11. Создать run/task workflows для реальной работы.
12. Создать custom processes, если встроенной механики недостаточно.

Не начинайте с platform contract, если его обязательные packages, templates,
tools, MCP servers, processes, coding standards или capabilities ещё не
существуют. Сначала создайте или зарегистрируйте зависимости, затем собирайте
platform.

## Поддерживаемые Мастера И Команды Создания

ProcessForge сейчас поддерживает file-first creation flows для:

- workplace initialization: `workplace-init` / `init-workplace`
- guided workplace setup: `workplace-setup start`, `workplace-setup review`,
  `workplace-setup apply` и `workplace-setup status`
- project onboarding: `project-onboard` / `init-project`
- first run bootstrap: `first-run`
- process authoring: `process-authoring-start`, `process-authoring-review`,
  `process-authoring-apply` и one-command `process-create`
- knowledge packages: `knowledge-package-create`, `knowledge-add-url`,
  `knowledge-add-resource`, `knowledge-index-refresh`, `knowledge-package-doctor`
- reusable templates: `template-create`, `template-add`, `template-doctor`
- platform contracts: `platform-create`, `platform-contract-install`,
  `platform-contract-doctor`
- tools и MCP providers: `tool-register`, `mcp-register`
- runs, tasks и iterations: `run-create`, `task-create`, `iteration-add`,
  completion, summary и doctor commands
- multi-agent orchestration: `orchestrator-plan create`,
  `orchestrator-plan validate`, `orchestrator-plan apply`,
  `orchestrator-plan status` и `worker-launch-prompt create`
- agent ledger и handoffs: `agent-register`, `agent-checkin`,
  `agent-availability`, `agent-lease-grant`, `process-route-list`,
  `handoff-create`, `handoff-status` и `agent-director-tick`
- primary agent sessions: `session-start`, `session-heartbeat`,
  `session-status` и `session-end`
- orchestrator shell agents: `orchestrator-shell-plan-create`,
  `orchestrator-shell-plan-validate` и `orchestrator-shell-plan-apply`
- runtime drivers и worker execution: `runtime-driver list`,
  `runtime-driver validate`, `worker-run prepare`, `worker-run start`,
  `worker-run status`, `worker-run collect`, `supervisor tick`,
  `supervisor run`, а также semantic aliases `execution-inspector-tick` и
  `execution-inspector-run`

`supervisor` - историческое техническое имя команды для Process Execution
Inspector. Он проверяет assigned worker runtime state; это не Agent Director.
Граница ответственности описана в
[docs/ru/concepts/director-ledger-inspector-boundary.md](docs/ru/concepts/director-ledger-inspector-boundary.md).

Флаг `--interactive` принимается командами first-run initialization для
совместимости UX, но текущая реализация остаётся file-first и не требует
terminal prompting.

## Prompts Для Оператора

### Подготовить Workplace

```text
Подготовь ProcessForge на этой машине.

Найди установленный ProcessForge tool root или распакованный distribution,
прочитай human README, затем используй docs/ru/getting-started/agent-prompts.md
для точных команд.

Создай или проверь workplace, запусти нужные doctor checks и сообщи:
- ProcessForge tool root;
- путь workplace;
- готов ли workplace;
- какой prompt использовать дальше для подключения проекта.

Держи ProcessForge установленным инструментом. Не копируй весь репозиторий в
agent configuration folders или в project repositories.
```

### Подключить Проект

```text
Подключи этот проект к существующему ProcessForge workplace.

Сначала изучи проект, выбери консервативный project type, создай проектный
слой .pf, прочитай .pf/START_AGENT_HERE.md, запусти doctor checks и кратко
опиши, что ProcessForge теперь знает о проекте.

Глобальные ресурсы держи в workplace. Не копируй тяжёлые документации, source
mirrors, toolchains или репозиторий ProcessForge внутрь проекта.
```

### Собрать Platform Stack

```text
Создай ProcessForge resources, которые нужны platform этого проекта.

Иди dependency-first: зарегистрируй tools и MCP servers, создай или импортируй
knowledge packages, создай reusable templates, затем создай platform contract,
который композирует эти resources. Если у platform есть parent и child,
опиши наследование в platform manifests и докажи его через platform doctor и
project snapshot.
```

### Начать Рабочую Сессию

```text
Начни ProcessForge run для этой работы.

Сначала прочитай .pf/START_AGENT_HERE.md. Создай run, разбей работу на явные
tasks, фиксируй work/debug/fix/review iterations, сохраняй artifacts и handoffs
в проектной .pf папке, а в конце сделай run summary и doctor check.
```

### Создать Процесс

```text
Создай новый ProcessForge process для этого проекта.

Используй process authoring workflow. Спрашивай недостающие решения,
поддерживай authoring answers и draft process в актуальном состоянии, проверь
semantic parity, применяй process только после review и докажи, что его можно
вывести в списке, описать и использовать для run.
```

## Карта Документации

- [Quickstart prompts](QUICKSTART.ru.md)
- [Индекс документации](docs/ru/index.md)
- [Установка и требования](docs/ru/getting-started/installation.md)
- [Порядок инициализации](docs/ru/getting-started/initialization-order.md)
- [Агентский command runbook](docs/ru/getting-started/agent-prompts.md)
- [Workplace vs project](docs/ru/concepts/workplace-vs-project.md)
- [Runtime model](docs/ru/concepts/runtime-model.md)
- [Модель агентской сессии](docs/ru/concepts/agent-session-model.md)
- [Platform contracts](docs/ru/concepts/platform-contracts.md)
- [Platform inheritance](docs/ru/concepts/platform-inheritance.md)
- [Навигация knowledge resources](docs/ru/concepts/knowledge-resource-navigation.md)
- [Runs, tasks и iterations](docs/ru/concepts/runs-tasks-iterations.md)
- [Authoring parity](docs/ru/authoring/authoring-parity.md)
- [Ограничения](docs/ru/known-limitations.md)

## Требования

Runtime requirements:

- Рекомендуется Python 3.11+.
- Python 3.10+ допустим только если текущие tests подтверждают совместимость.
- Python package dependencies из `requirements.txt`, сейчас `PyYAML`.
- Нужна файловая система с UTF-8.
- Пользователю или агенту нужен read/write access к ProcessForge distribution,
  workplace и project folders.
- Для runtime-использования PowerShell не требуется.
- В file-only mode ProcessForge не требует daemon или background process.

Development and release-check requirements:

- Python 3.11+.
- Python package dependencies из `requirements.txt`.
- Git для source installation и release checks, например `git diff --check`.
- Возможность запускать subprocesses и создавать temporary directories.
- ZIP support из стандартной библиотеки Python.

Optional integrations: MCP servers, external tools, browser checks и
version-control workflows. Runtime usage from a release archive не требует Git,
если пользователю не нужна version-control integration.

## ProcessForge И Agent Environments

Не копируйте весь репозиторий ProcessForge в `.codex`, `.claude`, `.agents` или
похожие папки конфигурации агентов.

Установите ProcessForge один раз как инструмент, инициализируйте workplace и
добавьте короткую инструкцию в конфигурацию агента: где установлен ProcessForge
и что проектные инструкции находятся в `.pf/START_AGENT_HERE.md`.

## Лицензия

См. [LICENSE](LICENSE).
