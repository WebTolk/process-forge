# Prompts быстрого старта ProcessForge

Этот quickstart написан для человека. Скопируйте нужный prompt в ИИ-агента.
Полный набор команд агент должен брать из
[docs/ru/getting-started/agent-prompts.md](docs/ru/getting-started/agent-prompts.md).

## 1. Подготовить инструмент

```text
Подготовь ProcessForge на этой машине.

Найди ProcessForge checkout или распакованный distribution, изучи README и
используй docs/ru/getting-started/agent-prompts.md как operational command
runbook.

Проверь, что distribution root пригоден к работе, и назови точный путь, который
мне нужно использовать как <processforge-root>.
```

## 2. Настроить workplace через диалог

```text
Настрой ProcessForge workplace через guided dialogue.

Используй агентский command runbook ProcessForge и считай `workplace-setup`
путём по умолчанию. Задавай вопросы небольшими блоками, записывай или обновляй
`answers.yaml`, генерируй `proposal.md`, показывай proposal перед apply и
запускай `workplace-setup apply --apply` только после подтверждения.

Создай workplace по указанному мной пути или предложи понятный локальный путь.
Запусти doctor-workplace, исправь структурные проблемы, которые можно безопасно
исправить, и сообщи результат.

Держи порядок: сначала workplace, затем resources, затем project. До создания
knowledge packages, templates или platform contracts настрой path constants,
package roots, knowledge roots, tool registries и MCP registries. Не подключай
проект, пока workplace resources не готовы.
```

Семейство команд guided setup: `workplace-setup start`,
`workplace-setup review`, `workplace-setup apply` и
`workplace-setup status`.

## 3. Полностью автоматическая настройка

```text
Настрой ProcessForge автоматически.

Используй явно переданные мной пути и ответы. Не запускай guided dialogue, если
не отсутствует обязательный ответ. Проверь tool root, инициализируй или проверь
workplace, настрой roots, создай или зарегистрируй shared resources, создай
platform contracts после их зависимостей и только потом подключи проект, если я
передал project path.

Выбирай консервативно, записывай assumptions в отчёт, запускай doctor checks и
сообщай, какие области настройки были пропущены или требуют ручных решений.
```

## 4. Создать общие resources

```text
Создай shared ProcessForge resources для этого workplace.

Спроси, какие resources нужны: knowledge packages, reusable templates, tools,
MCP providers, platform contracts или всё сразу.

Иди dependency-first. Зарегистрируй tools и MCP providers, создай или импортируй
knowledge packages, создай reusable templates, затем создай platform contracts,
которые композируют эти resources для конкретного project context.
```

## 5. Подключить проект

```text
Подключи этот репозиторий к ProcessForge.

Сначала изучи структуру репозитория, выбери консервативный project type,
подключи его к существующему workplace и сначала проверь, что нужные workplace
resources уже есть или явно не входят в scope.

Создай project-local .pf layer, прочитай созданный .pf/START_AGENT_HERE.md,
запусти doctor-project, refresh project context и кратко опиши, что
ProcessForge теперь знает о проекте.
```

## 6. Собрать platform stack

```text
Собери project platform stack в ProcessForge.

Используй platform contracts как composition manifests. Если у stack есть
parent и child platform, опиши parent/child relationship в extends или
requires.platforms. Подключи knowledge packages, templates, tools, MCP
providers, capabilities, processes, coding standards и project type hints по id.
Запусти platform doctor и затем refresh project context snapshot.
```

## 7. Начать run

```text
Создай ProcessForge run для моего текущего запроса.

Используй стандартную single-agent session model: один operator, одна primary
agent session, один project и один active process/run. Начни сессию через
session-start или agent-checkin, выполняй процесс последовательно, используй
CLI checks и gates как проверку, и сделай checkout перед завершением. Не
предполагай Agent Director или Supervisor, если process явно не использует
multi-agent, handoff или external runtime-worker mechanics.

Если workplace поддерживает Director, сначала проверь effective mode проекта:

```bash
python bin/pf.py project-mode status --project-root <project-root> --workplace <workplace-root>
python bin/pf.py project-mode set --project-root <project-root> --mode simple
python bin/pf.py project-mode set --project-root <project-root> --mode organized --init-office
```

Используй task-batch execution. Разбей работу на tasks, фиксируй iterations по
ходу работы, записывай artifacts/reviews/handoffs там, где этого требует
процесс, и заверши run-summary и run-doctor.
```

## 8. Создать собственный process

```text
Создай новый ProcessForge process.

Используй process authoring flow, а не ручное написание YAML первым шагом.
Спроси цель процесса, stages, roles, gates, artifacts, нужные знания и
ожидаемый task loop. Проверь draft, примени его и проверь итоговый process.
```

## 9. Использовать subagents

```text
Спланируй ProcessForge-assisted multi-agent run.

Используй встроенный multi-agent orchestration flow. Создай и проверь
orchestrator task plan, примени его для создания worker assignments и capsules,
запусти каждого worker только с его worker launch prompt и сведи outputs в
integration report перед delivery.
```

## 10. Agent ledger и process handoffs

```text
Спланируй ProcessForge handoff с agent attendance tracking.

Зарегистрируй workplace agents, отметь check-in для нужных roles, создай или
проверь .pf/process-routes.yaml, создай handoff package, запусти
agent-director-tick для выдачи leases, если нужная role online, и возвращай
только конкретные expected artifacts.
```

## 11. Проверить перед delivery

```text
Проверь репозиторий перед delivery.

Используй ProcessForge release и validation runbook для агентов. Запусти нужные
проверки, пересобери release archive с нейтральным именем, проверь архив и
сообщи точные pass/fail evidence перед commit или push.
```

## 12. Runtime driver and execution inspector smoke

```text
Используй ProcessForge runtime drivers для ограниченного execution-inspected test run.

Проверь built-in neutral runtime drivers, создай или используй orchestrator
plan с runtime.default_driver = test-echo-worker, запусти Process Execution
Inspector на малое число ticks и сообщи worker-run status files и produced
reports. Совместимые технические команды: `supervisor tick` и `supervisor run`;
более ясные aliases: `execution-inspector-tick` и `execution-inspector-run`.
```

## Обязательный порядок

1. Install ProcessForge distribution.
2. Verify ProcessForge itself.
3. Для human-led setup по умолчанию запустить guided workplace setup; direct
   workplace-init использовать только для явно автоматического пути.
4. Configure path constants and roots.
5. Configure knowledge roots.
6. Register tools and MCP servers.
7. Create/import knowledge packages.
8. Create reusable templates.
9. Create platform contracts.
10. Onboard project.
11. Create run/task workflow.
12. Create custom processes as needed.
13. Configure update sites, если packages, tools или workplace resources должны
    получать operator-controlled updates.

Capabilities описывают нужные действия, knowledge packages - где читать
правила, а platform contracts собирают application/domain stacks для проектов.
Base technologies являются knowledge packages и capabilities, а не platform
contracts.

Ядро ProcessForge domain-agnostic. Platforms, inheritance, package dependencies
и detection rules приходят из manifests и policy data.

Для проверки обновлений начните с `python bin/pf.py update candidates refresh
--workplace <workplace>`, затем используйте `stage`, `verify`, `apply
--confirm` или `rollback` по сценарию из
`docs/ru/getting-started/update-system.md`.

Не копируйте весь репозиторий ProcessForge в `.codex`, `.claude`, `.agents` или
похожие папки конфигурации агентов. Установите ProcessForge один раз как
инструмент и укажите агенту, где он установлен; проектные инструкции находятся
в `.pf/START_AGENT_HERE.md`.
# Project context lock

При onboarding агент должен выполнить `project-context-check --session-start
--json` после refresh snapshot. Работу можно продолжать при `fresh`, новые
версии ресурсов дают `fresh_with_updates`, rolling/current изменения дают
`stale`, а исчезнувшие pinned resources дают `broken`. Capsules закрепляют
snapshot id/checksum и не используют `latest`.
