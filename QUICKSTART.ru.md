# Промпты быстрого старта ProcessForge

Этот быстрый старт написан для человека. Скопируйте нужный промпт в ИИ-агента.
Полный набор команд агент должен брать из
[docs/ru/getting-started/agent-prompts.md](docs/ru/getting-started/agent-prompts.md).

## 1. Подготовить инструмент

```text
Подготовь ProcessForge на этой машине.

Найди checkout ProcessForge или распакованный дистрибутив, изучи README и
используй docs/ru/getting-started/agent-prompts.md как командный справочник.

Проверь, что корень дистрибутива пригоден к работе, и назови точный путь,
который мне нужно использовать как <processforge-root>.
```

## 2. Настроить workplace через диалог

```text
Настрой ProcessForge на этом устройстве пошагово.
```

Семейство команд пошаговой настройки: `workplace-setup start`,
`workplace-setup review`, `workplace-setup apply` и
`workplace-setup status`.

## 3. Полностью автоматическая настройка

```text
Настрой ProcessForge на этом устройстве в полностью автоматическом режиме.
Сначала исследуй текущий AGENTS.md и навыки для настройки.
```

В автоматическом режиме агент сначала объясняет, что где лежит и какую роль
имеет, предлагает сценарий настройки, получает подтверждение и только потом
применяет изменения.

## 4. Создать общие ресурсы

```text
Создай общие ресурсы ProcessForge для этого workplace.

Спроси, какие ресурсы нужны: пакеты знаний, повторно используемые шаблоны,
инструменты, MCP providers, platform contracts или всё сразу.

Иди от зависимостей. Зарегистрируй инструменты и MCP providers, создай или
импортируй пакеты знаний, создай повторно используемые шаблоны, затем создай
platform contracts, которые собирают эти ресурсы для конкретного project
context.
```

## 5. Подключить проект

```text
Подключи этот репозиторий к ProcessForge.

Сначала изучи структуру репозитория, выбери консервативный project type,
подключи его к существующему workplace и проверь, что нужные ресурсы workplace
уже есть или явно не входят в область работы.

Создай проектный слой .pf, прочитай созданный .pf/START_AGENT_HERE.md, запусти
doctor-project, обнови project context и кратко опиши, что ProcessForge теперь
знает о проекте.
```

## 6. Собрать platform stack

```text
Собери project platform stack в ProcessForge.

Используй platform contracts как композиционные манифесты. Если у стека есть
parent и child platform, опиши связь parent/child в extends или
requires.platforms. Подключи пакеты знаний, шаблоны, инструменты, MCP providers,
capabilities, процессы, стандарты кода и project type hints по id. Запусти
platform doctor и затем обнови снимок project context.
```

## 7. Начать run

```text
Создай ProcessForge run для моего текущего запроса.

Используй стандартную single-agent session model: один оператор, одна primary
agent session, один проект и один active process/run. Начни сессию через
session-start или agent-checkin, выполняй процесс последовательно, используй CLI
checks и gates как проверку и сделай checkout перед завершением. Не предполагай,
что Agent Director или Supervisor доступны, если process явно не использует
multi-agent, handoff или external runtime-worker mechanics.

Если workplace поддерживает Director, сначала проверь effective mode проекта:

```bash
python bin/pf.py project-mode status --project-root <project-root> --workplace <workplace-root>
python bin/pf.py project-mode set --project-root <project-root> --mode simple
python bin/pf.py project-mode set --project-root <project-root> --mode organized --init-office
```

Используй task-batch execution. Разбей работу на задачи, фиксируй итерации по
ходу работы, записывай артефакты, проверки и handoffs там, где этого требует
процесс, и заверши run-summary и run-doctor.
```

### Режим гаража с инструментами

Для обычной работы используйте образ гаража с инструментами: один оператор,
один основной агент, один проект и один активный process/run. Агент работает
последовательно, сам берёт нужные инструменты и знания, ведёт артефакты,
запускает проверки и возвращает результат без Agent Director.

Шаблон промпта:

```text
Инициализируй проект по ProcessForge, подключи все необходимые инструменты и
знания, мы делаем <название того, что делаем>. Заполняй все требуемые артефакты.
```

Пример для Joomla:

```text
Инициализируй проект по ProcessForge, подключи все необходимые инструменты и
знания для разработки Joomla-плагина. Мы делаем системный плагин Joomla,
который добавляет проверяемую интеграцию с внешним API. Заполняй все требуемые
артефакты, фиксируй архитектурные решения, изменения кода, проверки и результат
поставки.
```

### Режим кузницы или фабрики

Для сложной работы используйте образ кузницы или фабрики. В этом режиме
несколько агентов работают параллельно, получают изолированные задачи, а Agent
Director координирует маршруты, передачи и возвраты результатов. Agent Ledger
ведёт журнал вахтёра: кто вошёл в работу, кто активен, кому выдана lease и куда
нужно вернуть результат. Такой режим нужен для ветвлений, дочерних процессов,
возврата в родительский процесс и задач, где параллельность важнее простоты.

## 8. Создать собственный process

```text
Создай новый ProcessForge process.

Используй process authoring flow, а не ручное написание YAML первым шагом.
Спроси цель процесса, стадии, роли, gates, артефакты, нужные знания и ожидаемый
task loop. Проверь черновик, примени его и проверь итоговый process.
```

## 9. Использовать subagents

```text
Спланируй multi-agent run с поддержкой ProcessForge.

Используй встроенный сценарий multi-agent orchestration. Создай и проверь
orchestrator task plan, примени его для создания worker assignments и capsules,
запусти каждого worker только с его worker launch prompt и сведи результаты в
интеграционный отчёт перед delivery.
```

## 10. Agent ledger и process handoffs

```text
Спланируй ProcessForge handoff с учётом присутствия агентов.

Зарегистрируй workplace agents, отметь check-in для нужных ролей, создай или
проверь .pf/process-routes.yaml, создай handoff package, запусти
agent-director-tick для выдачи leases, если нужная роль online, и возвращай
только конкретные ожидаемые артефакты.
```

## 11. Проверить перед delivery

```text
Проверь репозиторий перед delivery.

Используй справочник ProcessForge по релизу и проверкам для агентов. Запусти
нужные проверки, пересобери релизный архив с нейтральным именем, проверь архив
и сообщи точные свидетельства pass/fail перед commit или push.
```

## 12. Runtime driver and execution inspector smoke

```text
Используй ProcessForge runtime drivers для ограниченного test run под
наблюдением Execution Inspector.

Проверь встроенные нейтральные runtime drivers, создай или используй
orchestrator plan с runtime.default_driver = test-echo-worker, запусти Process
Execution Inspector на малое число ticks и сообщи worker-run status files и
полученные отчёты. Совместимые технические команды: `supervisor tick` и `supervisor run`;
более ясные aliases: `execution-inspector-tick` и `execution-inspector-run`.
```

## Обязательный порядок

1. Установить дистрибутив ProcessForge.
2. Проверить сам ProcessForge.
3. Для настройки с участием человека по умолчанию запустить пошаговую настройку
   workplace; direct workplace-init использовать только для явно автоматического
   пути.
4. Настроить константы путей и корневые каталоги.
5. Настроить корни знаний.
6. Зарегистрировать инструменты и MCP servers.
7. Создать или импортировать пакеты знаний.
8. Создать повторно используемые шаблоны.
9. Создать platform contracts.
10. Подключить проект.
11. Создать рабочий сценарий run/task.
12. Создать собственные процессы, если они нужны.
13. Настроить update sites, если packages, tools или ресурсы workplace должны
    получать обновления под контролем оператора.

Capabilities описывают нужные действия, пакеты знаний - где читать правила, а
platform contracts собирают прикладные или предметные стеки для проектов. Base
technologies являются knowledge packages и capabilities, а не platform
contracts.

Ядро ProcessForge не зависит от предметной области. Platforms, inheritance,
package dependencies и detection rules приходят из manifests и policy data.

Для проверки обновлений начните с `python bin/pf.py update candidates refresh
--workplace <workplace>`, затем используйте `stage`, `verify`, `apply
--confirm` или `rollback` по сценарию из
`docs/ru/getting-started/update-system.md`.

Не копируйте весь репозиторий ProcessForge в `.codex`, `.claude`, `.agents` или
похожие папки конфигурации агентов. Установите ProcessForge один раз как
инструмент и укажите агенту, где он установлен; проектные инструкции находятся
в `.pf/START_AGENT_HERE.md`.
# Lock-модель project context

При подключении проекта агент должен выполнить `project-context-check
--session-start --json` после обновления снимка. Работу можно продолжать при
`fresh`, новые версии ресурсов дают `fresh_with_updates`, rolling/current
изменения дают `stale`, а исчезнувшие pinned resources дают `broken`. Capsules
закрепляют snapshot id/checksum и не используют `latest`.
