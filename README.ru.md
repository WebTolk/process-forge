# ProcessForge

<div align="center">

**Фреймворк для создания ИИ-процессов, независимый от конкретных платформ и ИИ-провайдеров.**

[![Версия](https://img.shields.io/badge/version-1.0.0-2F6FED?style=for-the-badge)](VERSION)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](requirements.txt)
[![Лицензия](https://img.shields.io/badge/license-Apache--2.0-blue?style=for-the-badge)](LICENSE)
[![File First](https://img.shields.io/badge/runtime-file--first-2E7D32?style=for-the-badge)](docs/ru/concepts/runtime-model.md)
[![Platform Neutral](https://img.shields.io/badge/core-platform--neutral-6A1B9A?style=for-the-badge)](docs/ru/concepts/domain-neutral-core.md)
[![Provider Neutral](https://img.shields.io/badge/AI-provider--neutral-455A64?style=for-the-badge)](docs/ru/concepts/runtime-drivers.md)

**Документация на английском:** [README.md](README.md)

</div>

ProcessForge - файловый фреймворк для создания, версионирования и выполнения
ИИ-процессов. Он не зависит от конкретных платформ реализации и ИИ-провайдеров:
предметные области, toolchains, knowledge packages, шаблоны, runtime drivers и
platform contracts подключаются через версионируемые файлы, а не зашиваются в
ядро.

Этот README написан для человека. ИИ-агенты должны использовать командный
справочник в
[docs/ru/getting-started/agent-prompts.md](docs/ru/getting-started/agent-prompts.md);
там перечислены только команды и механики, подтверждённые текущей кодовой базой.

![Схема рабочего места ProcessForge](docs/assets/processforge-architecture.svg)

## Зачем это нужно

ProcessForge превращает повторяемую ИИ-работу в явные process assets:

- формальные описания процессов со стадиями, ролями, артефактами, gates,
  capabilities, инструментами, hooks и правилами handoff;
- проектный слой `.pf/` для assignments, runs, tasks, iterations, artifacts,
  reviews, logs, handoffs, snapshots и закрытых runtime-данных;
- формализованные знания через knowledge packages, resource indexes, source
  metadata, load policies и update policies;
- reusable templates, tool registrations, MCP registrations, runtime drivers и
  platform contracts, которые собирают контекст проекта без hardcode в ядре;
- каскадное вычисление контекста из workplace и project resources в locked
  snapshots, assignment capsules, resolved rules и parameters;
- версионируемые файлы, checksums, release manifests, archive validation и
  обновление ресурсов из объявленных источников.

В результате workflow остаётся видимым в Git для человека и исполнимым для
ИИ-агента без скрытого SaaS backend, одного обязательного model provider или
одной конкретной продуктовой платформы.

## Два режима работы

### Режим гаража (1-1-1-1)

Обычный режим: один оператор, один основной agent session, один проект и один
активный process/run. Основной агент выполняет работу, запускает проверки,
ведёт артефакты и завершает с summary или handoff.

### Режим Кузницы / Фабрики

Режим для разделения работы на независимые ветки. Orchestrator создаёт
ограниченные assignments и capsules, запускает или координирует worker sessions,
собирает их outputs и интегрирует результат через handoffs и reviews.

## Быстрый старт

### Получить ProcessForge

Скачайте release archive из репозитория:

```bash
curl -L -o processforge.zip https://github.com/WebTolk/process-forge/raw/main/dist/processforge.zip
```

Или клонируйте репозиторий, если хотите работать из исходников:

```bash
git clone https://github.com/WebTolk/process-forge.git
```

### Установить как инструмент

Положите ProcessForge в стабильный каталог инструментов и распакуйте архив:

```bash
mkdir -p <tools-root>/processforge
unzip processforge.zip -d <tools-root>/processforge
python <tools-root>/processforge/bin/pf.py version
```

Для source checkout используйте корень репозитория как `<processforge-root>`:

```bash
python <processforge-root>/bin/pf.py version
```

### Стартовый промпт для агента

Для пошаговой настройки скопируйте в ИИ-агента:

```text
Инициализируй ProcessForge в пошаговом режиме. Он находится в папке
<путь-к-processforge>.
```

Для полностью автоматической настройки используйте этот вариант только когда
целевые пути уже известны и агент должен сначала изучить существующие
инструкции и ресурсы:

```text
Инициализируй ProcessForge в полностью автоматическом режиме. Он находится в
папке <путь-к-processforge>. Сначала исследуй текущий AGENTS.md и навыки для
настройки.
```

После готовности workplace подключите проект:

```text
Подключи этот проект к существующему ProcessForge workplace.

Сначала изучи проект, выбери консервативный project type, создай проектный
слой .pf, прочитай .pf/START_AGENT_HERE.md, запусти doctor checks и кратко
опиши, что ProcessForge теперь знает о проекте.

Глобальные ресурсы держи в workplace. Не копируй тяжёлую документацию, зеркала
исходного кода, toolchains или репозиторий ProcessForge внутрь проекта.
```

Внутри подключённого проекта начинайте каждую ProcessForge-сессию с
`.pf/START_AGENT_HERE.md`.

Больше стартовых промптов: [QUICKSTART.ru.md](QUICKSTART.ru.md).

## Рабочая модель

### Что такое ProcessForge

Рабочее место (workplace) - это физическая или виртуальная машина, где работают
человек и ИИ-агенты: компьютер, ноутбук, сервер или узел выполнения. ProcessForge
устанавливается один раз как инструмент этого рабочего места.

Workplace хранит общие ресурсы машины: описания процессов, пакеты знаний,
повторно используемые шаблоны, регистрации инструментов, регистрации MCP,
платформенные контракты, корневые пути, реестры, кэш, события выполнения и
журналы.

Каждый проект хранит собственный слой `.pf/`. Проектный слой содержит project
context, выбранные глобальные ресурсы, назначения, запуски, задачи, итерации,
артефакты, проверки, передачи, hooks и закрытые файлы среды выполнения.

Project context имеет lock-модель. `.pf/process-forge.yaml` объявляет
`context_requirements`; `project-context-refresh` записывает разрешённый lock в
`.pf/contexts/project-context.snapshot.yaml` и поколения в
`.pf/contexts/project-context.snapshots/`. `project-context-check` возвращает
`fresh`, `fresh_with_updates`, `stale` или `broken`; assignment capsules
закрепляют snapshot id/checksum и не перепривязываются при последующих
обновлениях.

### Как связаны слои

Используйте ProcessForge снаружи внутрь:

1. ProcessForge tool root: установленный CLI, встроенные процессы, схемы,
   проверки, документация и шаблоны промптов.
2. Workplace: состояние машины и повторно используемые ресурсы, общие для
   проектов.
3. Ресурсы workplace: корни и пакеты знаний, шаблоны, инструменты, MCP
   providers, корни пакетов, описания процессов и платформенные контракты.
4. Project `.pf/`: project context, выбранные ресурсы, назначения, запуски,
   задачи, итерации, артефакты, проверки, передачи и hooks.

Проектный слой зависит от workplace. В проект не нужно копировать исходники
ProcessForge, тяжёлые зеркала документации, общие toolchains или содержимое
глобальных ресурсов.

### Порядок инициализации

Для нового рабочего места используйте такой порядок:

1. Установить дистрибутив ProcessForge.
2. Проверить дистрибутив ProcessForge.
3. По умолчанию запустить пошаговую настройку workplace с участием человека.
4. Настроить константы путей и корневые каталоги.
5. Настроить корни знаний, особенно корни локальной документации.
6. Зарегистрировать инструменты и MCP servers.
7. Создать или импортировать пакеты знаний.
8. Создать повторно используемые шаблоны.
9. Создать platform contracts из уже готовых ресурсов.
10. Подключить проекты к workplace.
11. Создать рабочие сценарии run/task для реальной работы.
12. Создать собственные процессы, если встроенной механики недостаточно.

Не начинайте с platform contract, если его обязательные packages, templates,
tools, MCP servers, processes, coding standards или capabilities ещё не
существуют. Сначала создайте или зарегистрируйте зависимости, затем собирайте
платформу.

Используйте `workplace-setup` как путь по умолчанию, когда ИИ-агент настраивает
новую машину вместе с человеком. Агент задаёт вопросы блоками, пишет
`answers.yaml`, готовит `proposal.md`, просит подтверждение, применяет
workplace, запускает `doctor-workplace` и только потом переходит к созданию
ресурсов или подключению проекта.

Папка запуска агента не задаёт роль в ProcessForge. При настройке машины агент
должен явно различать путь установленного дистрибутива ProcessForge, корень
workplace, необязательный корень глобальных агентных инструкций и реальные
корни проектов. Папки `.codex`, `.claude`, `.agents` или любые пользовательские
agent root могут быть источниками инструкций или знаний, но не становятся
проектами без явной команды `project-onboard`.

Используйте `first-run`, `workplace-init` и прямые create/register команды как
полностью автоматический путь только когда оператор явно просит автоматизацию и
даёт нужные пути и ответы.

## Режимы работы подробно

### Режим гаража (1-1-1-1)

Атомарная единица выполнения - `1-1-1-1`: один человек-оператор, один основной
agent session, один project и один активный process/run. В обычном single-agent
flow основной агент выполняет работу, запускает CLI checks, пишет артефакты и
завершает с checkout; Worker и Inspector остаются фазами или проверками той же
сессии, а не отдельными участниками. Agent Ledger - это CLI/files, не отдельный
агент.

Базовый промпт:

```text
Инициализируй проект по ProcessForge, подключи все необходимые инструменты и
знания, мы делаем <название того, что делаем>. Заполняй все требуемые артефакты.
```

Начать рабочую сессию:

```text
Начни ProcessForge run для этой работы.

Сначала прочитай .pf/START_AGENT_HERE.md. Создай run, разбей работу на явные
задачи, фиксируй итерации work/debug/fix/review, сохраняй артефакты и передачи
в проектной папке .pf, а в конце сделай run summary и doctor check.
```

### Режим Кузницы / Фабрики

Workplace может быть Director-capable, а отдельные проекты при этом остаются
simple. Режим координации проекта вычисляется как `simple`, `organized` или
`inherit` от значения по умолчанию в workplace. `organized` нужен только тем
проектам, которые должны использовать Director Office рабочего места; simple
projects сохраняют обычный сценарий 1-1-1-1.

Director и Supervisor/Execution Inspector нужны только для multi-agent,
process-transition или external runtime-worker scenarios. Подробнее:
[модель агентской сессии](docs/ru/concepts/agent-session-model.md).

Для shell-agent plans `orchestrator-shell-plan-apply --model <model>` передаёт
одну выбранную model всем shell workers в applied plan.

## Основные строительные блоки

Process definitions описывают механику процесса. Это YAML-конструкторы с
произвольным количеством стадий, ролей, артефактов, контрольных ворот,
capabilities, разрешённых инструментов и hooks. Им не нужно называть конкретную
платформу реализации.

Platform contracts - композиционные сущности для конкретного проектного
контекста. Платформа может быть одиночной или составной: parent плюс child.
Контракт подключает обязательный и рекомендуемый стек пакетов знаний, шаблонов,
инструментов, MCP providers, capabilities, процессов, стандартов кода,
подсказок типа проекта и политик. Ядро ProcessForge разрешает эти контракты из
манифестов; в коде ядра нет жёсткой привязки к конкретным продуктам, CMS,
фреймворкам, маркетплейсам или предметным областям.

## Поддерживаемые мастера и команды создания

ProcessForge сейчас поддерживает файловые сценарии создания:

- workplace initialization: `workplace-init` / `init-workplace`
- guided workplace setup: `workplace-setup start`, `workplace-setup review`,
  `workplace-setup apply` и `workplace-setup status`
- project onboarding: `project-onboard` / `init-project`
- coordination modes: `workplace-mode status`, `workplace-mode set`,
  `project-mode status`, `project-mode set`, `director-inbox-submit`,
  `director-case-refresh` и `error-route`
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
Inspector. Он проверяет состояние выполнения назначенного worker; это не Agent
Director. Граница ответственности описана в
[docs/ru/concepts/director-ledger-inspector-boundary.md](docs/ru/concepts/director-ledger-inspector-boundary.md).

Флаг `--interactive` принимается командами first-run initialization ради
совместимости пользовательского опыта, но текущая реализация остаётся файловой
и не требует вопросов в терминале.

## Карта документации

Для человека:

- [Промпты быстрого старта](QUICKSTART.ru.md)
- [Установка и требования](docs/ru/getting-started/installation.md)
- [Пошаговая настройка workplace](docs/ru/getting-started/guided-workplace-setup.md)
- [Порядок инициализации](docs/ru/getting-started/initialization-order.md)
- [Workplace vs project](docs/ru/concepts/workplace-vs-project.md)
- [Создание ресурсов](docs/getting-started/resource-authoring.md)
- [Подключение проекта](docs/ru/getting-started/project-onboarding.md)
- [Этапы встроенных процессов](docs/ru/processes/built-in-processes.md)

Для ИИ-агентов:

- [Командный справочник агента](docs/ru/getting-started/agent-prompts.md)
- [Промпт агента для пошаговой настройки workplace](prompts/guided-workplace-setup-agent.md)
- [Промпт агента для автоматической инициализации workplace](prompts/workplace-initialization-agent.md)
- [Промпт агента для подключения проекта](prompts/project-onboarding-agent.md)
- [Чек-лист релиза](docs/release-checklist.md)

Подробный индекс:

- [Промпты быстрого старта](QUICKSTART.ru.md)
- [Индекс документации](docs/ru/index.md)
- [Установка и требования](docs/ru/getting-started/installation.md)
- [Порядок инициализации](docs/ru/getting-started/initialization-order.md)
- [Командный справочник агента](docs/ru/getting-started/agent-prompts.md)
- [Этапы встроенных процессов](docs/ru/processes/built-in-processes.md)
- [Вычисление контекста](docs/ru/concepts/context-resolution.md)
- [Каскадное объединение](docs/ru/concepts/cascade-merge.md)
- [Workplace vs project](docs/ru/concepts/workplace-vs-project.md)
- [Модель среды выполнения](docs/ru/concepts/runtime-model.md)
- [Модель агентской сессии](docs/ru/concepts/agent-session-model.md)
- [Режимы координации проекта](docs/ru/concepts/project-coordination-modes.md)
- [Платформенные контракты](docs/ru/concepts/platform-contracts.md)
- [Наследование платформ](docs/ru/concepts/platform-inheritance.md)
- [Навигация по ресурсам знаний](docs/ru/concepts/knowledge-resource-navigation.md)
- [Площадки обновлений](docs/ru/concepts/update-sites.md)
- [Жизненный цикл обновлений](docs/ru/concepts/update-lifecycle.md)
- [Система обновлений](docs/ru/getting-started/update-system.md)
- [Runs, tasks и iterations](docs/ru/concepts/runs-tasks-iterations.md)
- [Паритет authoring](docs/ru/authoring/authoring-parity.md)
- [Ограничения](docs/ru/known-limitations.md)

## Требования

Требования к среде выполнения:

- Рекомендуется Python 3.11+.
- Python 3.10+ допустим только если текущие tests подтверждают совместимость.
- Зависимости Python-пакетов описаны в `requirements.txt`, сейчас это `PyYAML`.
- Нужна файловая система с UTF-8.
- Пользователю или агенту нужен доступ на чтение и запись к дистрибутиву
  ProcessForge, workplace и каталогам проектов.
- Для обычного использования PowerShell не требуется.
- В файловом режиме ProcessForge не требует демона или фонового процесса.

Требования к разработке и проверкам релиза:

- Python 3.11+.
- Зависимости Python-пакетов из `requirements.txt`.
- Git для установки из исходного кода и проверок релиза, например
  `git diff --check`.
- Возможность запускать дочерние процессы и создавать временные каталоги.
- Поддержка ZIP из стандартной библиотеки Python.
- Тесты обновлений детерминированы: public release checks используют локальные
  file-provider fixtures и не требуют реальной сети.

Необязательные интеграции: MCP servers, внешние инструменты, проверки в браузере
и сценарии работы с системой контроля версий. Использование из релизного архива
не требует Git, если пользователю не нужна интеграция с системой контроля
версий.

## ProcessForge и агентские среды

Не копируйте весь репозиторий ProcessForge в `.codex`, `.claude`, `.agents` или
похожие папки конфигурации агентов.

Установите ProcessForge один раз как инструмент, инициализируйте workplace и
добавьте короткую инструкцию в конфигурацию агента: где установлен ProcessForge
и что проектные инструкции находятся в `.pf/START_AGENT_HERE.md`.

## Лицензия

ProcessForge распространяется по лицензии Apache License, Version 2.0. См.
[LICENSE](LICENSE) и [NOTICE](NOTICE).
