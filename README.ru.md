# ProcessForge

<div align="center">

**Фреймворк для создания ИИ-процессов, независимый от конкретных платформ и поставщиков ИИ.**

[![Версия](https://img.shields.io/badge/version-1.0.1-2F6FED?style=for-the-badge)](VERSION)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](requirements.txt)
[![Лицензия](https://img.shields.io/badge/license-Apache--2.0-blue?style=for-the-badge)](LICENSE)
[![Файловый режим](https://img.shields.io/badge/runtime-file--first-2E7D32?style=for-the-badge)](docs/ru/concepts/runtime-model.md)
[![Независимость от платформ](https://img.shields.io/badge/core-platform--neutral-6A1B9A?style=for-the-badge)](docs/ru/concepts/domain-neutral-core.md)
[![Независимость от провайдеров](https://img.shields.io/badge/AI-provider--neutral-455A64?style=for-the-badge)](docs/ru/concepts/runtime-drivers.md)

**Документация на английском:** [README.md](README.md)

</div>

ProcessForge - файловый фреймворк для создания, версионирования и выполнения
ИИ-процессов. Он не зависит от конкретных платформ реализации и поставщиков ИИ
(AI providers): предметные области, инструментальные цепочки (toolchains),
пакеты знаний (knowledge packages), шаблоны, драйверы выполнения
(runtime drivers) и платформенные контракты (platform contracts) подключаются
через версионируемые файлы, а не зашиваются в ядро.

Этот README написан для человека. ИИ-агенты должны использовать командный
справочник в
[docs/ru/getting-started/agent-prompts.md](docs/ru/getting-started/agent-prompts.md);
там перечислены только команды и механики, подтверждённые текущей кодовой базой.

![Схема рабочего места ProcessForge](docs/assets/processforge-architecture.svg)

## Зачем это нужно

ProcessForge превращает повторяемую ИИ-работу в явные процессные активы
(process assets):

- формальные описания процессов со стадиями, ролями, артефактами,
  контрольными воротами (gates), возможностями (capabilities), инструментами,
  событиями-перехватчиками (hooks) и правилами передачи результата (handoff);
- проектный слой `.pf/` для назначений (assignments), запусков (runs), задач
  (tasks), итераций (iterations), артефактов, проверок (reviews), журналов
  (logs), передач результата (handoffs), снимков контекста (snapshots) и
  закрытых данных выполнения (runtime data);
- формализованные знания через пакеты знаний (knowledge packages), индексы
  ресурсов (resource indexes), сведения об источниках (source metadata),
  правила загрузки (load policies) и правила обновления (update policies);
- повторно используемые шаблоны (reusable templates), регистрации инструментов,
  регистрации MCP, драйверы выполнения и платформенные контракты, которые
  собирают контекст проекта без жёсткой привязки в ядре;
- **каскадное вычисление контекста из рабочего места (workplace) и проектных
  ресурсов (project resources) в закреплённые снимки (locked snapshots),
  капсулы назначений (assignment capsules), вычисленные правила
  (resolved rules) и параметры (parameters);**
- версионируемые файлы, контрольные суммы (checksums), манифесты релиза
  (release manifests), проверку архива (archive validation) и обновление
  ресурсов из объявленных источников.

В результате рабочий процесс (workflow) остаётся видимым в Git для человека и
исполнимым для ИИ-агента без скрытого SaaS-сервиса, одного обязательного
поставщика модели (model provider) или одной конкретной продуктовой платформы.

## Два режима работы

### Режим гаража (1-1-1-1)

Обычный режим: один оператор, одна основная агентская сессия (agent session),
один проект и один активный процесс/запуск (process/run). Основной агент
выполняет работу, запускает проверки, ведёт артефакты и завершает её сводкой
(summary) или передачей результата (handoff).

### Режим Кузницы / Фабрики

Режим для разделения работы на независимые ветки. Оркестратор (orchestrator)
создаёт ограниченные назначения (assignments) и капсулы (capsules), запускает
или координирует рабочие сессии (worker sessions), собирает их результаты
(outputs) и интегрирует итог через передачи результата (handoffs) и проверки
(reviews).

## Быстрый старт

### Разместить ProcessForge

Скачайте релизный архив (release archive)
[dist/processforge.zip](dist/processforge.zip) и распакуйте его в стабильную
папку, доступную ИИ-агентам: например, в общую папку инструментов для агентов.
Используйте эту папку как `<processforge-root>` в промптах ниже.

Если вы работаете из рабочей копии исходного кода (source checkout), используйте
корень репозитория как `<processforge-root>`.

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

После готовности рабочего места (workplace) подключите проект:

```text
Подключи этот проект к существующему рабочему месту ProcessForge (workplace).

Сначала изучи проект, выбери консервативный тип проекта (project type), создай
проектный слой .pf, прочитай .pf/START_AGENT_HERE.md, запусти проверки
(doctor checks) и кратко опиши, что ProcessForge теперь знает о проекте.

Глобальные ресурсы держи в рабочем месте (workplace). Не копируй тяжёлую
документацию, зеркала исходного кода, инструментальные цепочки (toolchains) или
репозиторий ProcessForge внутрь проекта.
```

Внутри подключённого проекта начинайте каждую ProcessForge-сессию с
`.pf/START_AGENT_HERE.md`.

Больше стартовых промптов: [QUICKSTART.ru.md](QUICKSTART.ru.md).

## Рабочая модель

### Что такое ProcessForge

Рабочее место (workplace) - это физическая или виртуальная машина, где работают
человек и ИИ-агенты: компьютер, ноутбук, сервер или узел выполнения. ProcessForge
устанавливается один раз как инструмент этого рабочего места.

Рабочее место хранит общие ресурсы машины: описания процессов, пакеты знаний,
повторно используемые шаблоны, регистрации инструментов, регистрации MCP,
платформенные контракты, корневые пути, реестры, кэш, события выполнения и
журналы.

Каждый проект хранит собственный слой `.pf/`. Проектный слой содержит проектный
контекст (project context), выбранные глобальные ресурсы, назначения, запуски,
задачи, итерации, артефакты, проверки, передачи, перехватчики событий (hooks) и
закрытые файлы среды выполнения.

Проектный контекст (project context) имеет модель закрепления (lock model).
`.pf/process-forge.yaml` объявляет
`context_requirements`; `project-context-refresh` записывает вычисленный
lock-файл в
`.pf/contexts/project-context.snapshot.yaml` и поколения в
`.pf/contexts/project-context.snapshots/`. `project-context-check` возвращает
`fresh`, `fresh_with_updates`, `stale` или `broken`; капсулы назначений
(assignment capsules) закрепляют идентификатор снимка (snapshot id) и
контрольную сумму (checksum) и не перепривязываются при последующих обновлениях.

### Как связаны слои

Используйте ProcessForge снаружи внутрь:

1. Корень инструмента ProcessForge (tool root): установленный CLI, встроенные
   процессы, схемы, проверки, документация и шаблоны промптов.
2. Рабочее место (workplace): состояние машины и повторно используемые ресурсы,
   общие для проектов.
3. Ресурсы рабочего места: корни и пакеты знаний, шаблоны, инструменты,
   поставщики MCP (MCP providers), корни пакетов, описания процессов и
   платформенные контракты.
4. Проектный слой `.pf/`: проектный контекст, выбранные ресурсы, назначения,
   запуски, задачи, итерации, артефакты, проверки, передачи и перехватчики
   событий (hooks).

Проектный слой зависит от рабочего места. В проект не нужно копировать исходники
ProcessForge, тяжёлые зеркала документации, общие инструментальные цепочки
(toolchains) или содержимое глобальных ресурсов.

### Порядок инициализации

Для нового рабочего места используйте такой порядок:

1. Установить дистрибутив ProcessForge.
2. Проверить дистрибутив ProcessForge.
3. По умолчанию запустить пошаговую настройку рабочего места с участием
   человека.
4. Настроить константы путей и корневые каталоги.
5. Настроить корни знаний, особенно корни локальной документации.
6. Зарегистрировать инструменты и серверы MCP (MCP servers).
7. Создать или импортировать пакеты знаний.
8. Создать повторно используемые шаблоны.
9. Создать платформенные контракты из уже готовых ресурсов.
10. Подключить проекты к рабочему месту.
11. Создать рабочие сценарии запуск/задача (run/task) для реальной работы.
12. Создать собственные процессы, если встроенной механики недостаточно.

Не начинайте с платформенного контракта (platform contract), если его
обязательные пакеты, шаблоны, инструменты, серверы MCP, процессы, стандарты
кода или возможности (capabilities) ещё не существуют. Сначала создайте или
зарегистрируйте зависимости, затем собирайте платформу.

Используйте `workplace-setup` как путь по умолчанию, когда ИИ-агент настраивает
новую машину вместе с человеком. Агент задаёт вопросы блоками, пишет
`answers.yaml`, готовит `proposal.md`, просит подтверждение, применяет
настройки рабочего места, запускает `doctor-workplace` и только потом переходит
к созданию ресурсов или подключению проекта.

Папка запуска агента не задаёт роль в ProcessForge. При настройке машины агент
должен явно различать путь установленного дистрибутива ProcessForge, корень
рабочего места, необязательный корень глобальных агентных инструкций и реальные
корни проектов. Папки `.codex`, `.claude`, `.agents` или любые пользовательские
корни агента (agent root) могут быть источниками инструкций или знаний, но не
становятся проектами без явной команды `project-onboard`.

Используйте `first-run`, `workplace-init` и прямые команды создания/регистрации
(create/register) как полностью автоматический путь только когда оператор явно
просит автоматизацию и даёт нужные пути и ответы.

## Режимы работы подробно

### Режим гаража (1-1-1-1)

Атомарная единица выполнения - `1-1-1-1`: один человек-оператор, одна основная
агентская сессия, один проект и один активный процесс/запуск. В обычном
одноагентном потоке (single-agent flow) основной агент выполняет работу,
запускает CLI-проверки, пишет артефакты и завершает с отметкой выхода
(checkout); Worker и Inspector остаются фазами или проверками той же сессии, а
не отдельными участниками. Журнал агентов (Agent Ledger) - это CLI и файлы, а не
отдельный агент.

Базовый промпт:

```text
Инициализируй проект по ProcessForge, подключи все необходимые инструменты и
знания, мы делаем <название того, что делаем>. Заполняй все требуемые артефакты.
```

Начать рабочую сессию:

```text
Начни запуск ProcessForge (run) для этой работы.

Сначала прочитай .pf/START_AGENT_HERE.md. Создай run, разбей работу на явные
задачи, фиксируй итерации работы, отладки, исправления и проверки
(work/debug/fix/review), сохраняй артефакты и передачи в проектной папке .pf, а
в конце сделай сводку запуска (run summary) и проверку (doctor check).
```

### Режим Кузницы / Фабрики

Рабочее место может поддерживать директора (Director-capable), а отдельные
проекты при этом остаются простыми (simple). Режим координации проекта
вычисляется как `simple`, `organized` или `inherit` от значения по умолчанию в
рабочем месте. `organized` нужен только тем проектам, которые должны
использовать кабинет директора рабочего места (Director Office); простые
проекты сохраняют обычный сценарий 1-1-1-1.

Директор (Director) и инспектор выполнения (Supervisor/Execution Inspector)
нужны только для многоагентной работы (multi-agent), переходов между процессами
(process transitions) или сценариев с внешними рабочими процессами выполнения
(external runtime workers). Подробнее:
[модель агентской сессии](docs/ru/concepts/agent-session-model.md).

Для планов shell-агентов (shell-agent plans)
`orchestrator-shell-plan-apply --model <model>` передаёт одну выбранную модель
всем shell-исполнителям (shell workers) в применяемом плане (applied plan).

## Основные строительные блоки

Описания процессов (process definitions) задают механику процесса. Это
YAML-конструкторы с произвольным количеством стадий, ролей, артефактов,
контрольных ворот, возможностей (capabilities), разрешённых инструментов и
перехватчиков событий (hooks). Им не нужно называть конкретную платформу
реализации.

Платформенные контракты (platform contracts) - композиционные сущности для
конкретного проектного контекста. Платформа может быть одиночной или составной:
родитель (parent) плюс дочерняя платформа (child).
Контракт подключает обязательный и рекомендуемый стек пакетов знаний, шаблонов,
инструментов, поставщиков MCP, возможностей, процессов, стандартов кода,
подсказок типа проекта и политик. Ядро ProcessForge разрешает эти контракты из
манифестов; в коде ядра нет жёсткой привязки к конкретным продуктам, CMS,
фреймворкам, маркетплейсам или предметным областям.

## Поддерживаемые мастера и команды создания

ProcessForge сейчас поддерживает файловые сценарии создания:

- инициализация рабочего места (workplace initialization): `workplace-init` / `init-workplace`
- пошаговая настройка рабочего места (guided workplace setup): `workplace-setup start`, `workplace-setup review`,
  `workplace-setup apply` и `workplace-setup status`
- подключение проекта (project onboarding): `project-onboard` / `init-project`
- режимы координации (coordination modes): `workplace-mode status`, `workplace-mode set`,
  `project-mode status`, `project-mode set`, `director-inbox-submit`,
  `director-case-refresh` и `error-route`
- первый запуск (first run bootstrap): `first-run`
- создание процессов (process authoring): `process-authoring-start`, `process-authoring-review`,
  `process-authoring-apply` и команда полного создания `process-create`
- пакеты знаний (knowledge packages): `knowledge-package-create`, `knowledge-add-url`,
  `knowledge-add-resource`, `knowledge-index-refresh`, `knowledge-package-doctor`
- повторно используемые шаблоны (reusable templates): `template-create`, `template-add`, `template-doctor`
- платформенные контракты (platform contracts): `platform-create`, `platform-contract-install`,
  `platform-contract-doctor`
- инструменты и поставщики MCP: `tool-register`, `mcp-register`
- запуски, задачи и итерации (runs, tasks, iterations): `run-create`, `task-create`, `iteration-add`,
  команды завершения, сводки и проверки (doctor commands)
- многоагентная оркестрация (multi-agent orchestration): `orchestrator-plan create`,
  `orchestrator-plan validate`, `orchestrator-plan apply`,
  `orchestrator-plan status` и `worker-launch-prompt create`
- журнал агентов и передачи результата (agent ledger, handoffs): `agent-register`, `agent-checkin`,
  `agent-availability`, `agent-lease-grant`, `process-route-list`,
  `handoff-create`, `handoff-status` и `agent-director-tick`
- основные агентские сессии (primary agent sessions): `session-start`, `session-heartbeat`,
  `session-status` и `session-end`
- shell-агенты оркестратора (orchestrator shell agents): `orchestrator-shell-plan-create`,
  `orchestrator-shell-plan-validate` и `orchestrator-shell-plan-apply`
- драйверы и выполнение исполнителей (runtime drivers, worker execution): `runtime-driver list`,
  `runtime-driver validate`, `worker-run prepare`, `worker-run start`,
  `worker-run status`, `worker-run collect`, `supervisor tick`,
  `supervisor run`, а также смысловые псевдонимы (semantic aliases) `execution-inspector-tick` и
  `execution-inspector-run`

`supervisor` - историческое техническое имя команды для инспектора выполнения
(Process Execution Inspector). Он проверяет состояние выполнения назначенного
исполнителя (worker); это не директор агентов (Agent Director). Граница
ответственности описана в
[docs/ru/concepts/director-ledger-inspector-boundary.md](docs/ru/concepts/director-ledger-inspector-boundary.md).

Флаг `--interactive` принимается командами инициализации первого запуска
(first-run initialization) ради
совместимости пользовательского опыта, но текущая реализация остаётся файловой
и не требует вопросов в терминале.

## Карта документации

Для человека:

- [Промпты быстрого старта](QUICKSTART.ru.md)
- [Установка и требования](docs/ru/getting-started/installation.md)
- [Пошаговая настройка рабочего места (workplace)](docs/ru/getting-started/guided-workplace-setup.md)
- [Порядок инициализации](docs/ru/getting-started/initialization-order.md)
- [Рабочее место и проект (Workplace vs project)](docs/ru/concepts/workplace-vs-project.md)
- [Создание ресурсов](docs/getting-started/resource-authoring.md)
- [Подключение проекта](docs/ru/getting-started/project-onboarding.md)
- [Этапы встроенных процессов](docs/ru/processes/built-in-processes.md)

Для ИИ-агентов:

- [Командный справочник агента](docs/ru/getting-started/agent-prompts.md)
- [Промпт агента для пошаговой настройки рабочего места](prompts/guided-workplace-setup-agent.md)
- [Промпт агента для автоматической инициализации рабочего места](prompts/workplace-initialization-agent.md)
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
- [Рабочее место и проект (Workplace vs project)](docs/ru/concepts/workplace-vs-project.md)
- [Модель среды выполнения](docs/ru/concepts/runtime-model.md)
- [Модель агентской сессии](docs/ru/concepts/agent-session-model.md)
- [Режимы координации проекта](docs/ru/concepts/project-coordination-modes.md)
- [Платформенные контракты](docs/ru/concepts/platform-contracts.md)
- [Наследование платформ](docs/ru/concepts/platform-inheritance.md)
- [Навигация по ресурсам знаний](docs/ru/concepts/knowledge-resource-navigation.md)
- [Площадки обновлений](docs/ru/concepts/update-sites.md)
- [Жизненный цикл обновлений](docs/ru/concepts/update-lifecycle.md)
- [Система обновлений](docs/ru/getting-started/update-system.md)
- [Запуски, задачи и итерации (runs, tasks, iterations)](docs/ru/concepts/runs-tasks-iterations.md)
- [Паритет создания (authoring parity)](docs/ru/authoring/authoring-parity.md)
- [Ограничения](docs/ru/known-limitations.md)

## Требования

Требования к среде выполнения:

- Рекомендуется Python 3.11+.
- Python 3.10+ допустим только если текущие тесты подтверждают совместимость.
- Зависимости Python-пакетов описаны в `requirements.txt`, сейчас это `PyYAML`.
- Нужна файловая система с UTF-8.
- Пользователю или агенту нужен доступ на чтение и запись к дистрибутиву
  ProcessForge, рабочему месту и каталогам проектов.
- Для обычного использования PowerShell не требуется.
- В файловом режиме ProcessForge не требует демона или фонового процесса.

Требования к разработке и проверкам релиза:

- Python 3.11+.
- Зависимости Python-пакетов из `requirements.txt`.
- Git для установки из исходного кода и проверок релиза, например
  `git diff --check`.
- Возможность запускать дочерние процессы и создавать временные каталоги.
- Поддержка ZIP из стандартной библиотеки Python.
- Тесты обновлений детерминированы: публичные проверки релиза
  (public release checks) используют локальные фикстуры файлового поставщика
  (file-provider fixtures) и не требуют реальной сети.

Необязательные интеграции: серверы MCP, внешние инструменты, проверки в
браузере и сценарии работы с системой контроля версий. Использование из
релизного архива не требует Git, если пользователю не нужна интеграция с
системой контроля версий.

## ProcessForge и агентские среды

Не копируйте весь репозиторий ProcessForge в `.codex`, `.claude`, `.agents` или
похожие папки конфигурации агентов.

Установите ProcessForge один раз как инструмент, инициализируйте рабочее место
и добавьте короткую инструкцию в конфигурацию агента: где установлен
ProcessForge и что проектные инструкции находятся в `.pf/START_AGENT_HERE.md`.

## Лицензия

ProcessForge распространяется по лицензии Apache License, Version 2.0. См.
[LICENSE](LICENSE) и [NOTICE](NOTICE).
