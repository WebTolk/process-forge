# Prompts Быстрого Старта ProcessForge

Этот quickstart написан для человека. Скопируйте нужный prompt в ИИ-агента.
Полный набор команд агент должен брать из
[docs/ru/getting-started/agent-prompts.md](docs/ru/getting-started/agent-prompts.md).

## 1. Подготовить Инструмент

```text
Подготовь ProcessForge на этой машине.

Найди ProcessForge checkout или распакованный distribution, изучи README и
используй docs/ru/getting-started/agent-prompts.md как operational command
runbook.

Проверь, что distribution root пригоден к работе, и назови точный путь, который
мне нужно использовать как <processforge-root>.
```

## 2. Инициализировать Workplace

```text
Инициализируй ProcessForge workplace.

Используй агентский command runbook ProcessForge. Создай workplace по указанному
мной пути или предложи понятный локальный путь. Запусти doctor-workplace,
исправь структурные проблемы, которые можно безопасно исправить, и сообщи
результат.

До создания knowledge packages или platform contracts настрой path constants,
package roots, knowledge roots, tool registries и MCP registries.
```

Для диалоговой настройки машины используйте `workplace-setup start`,
просмотрите proposal, затем выполните `workplace-setup apply --apply`.

## 3. Создать Общие Resources

```text
Создай shared ProcessForge resources для этого workplace.

Спроси, какие resources нужны: knowledge packages, reusable templates, tools,
MCP providers, platform contracts или всё сразу.

Иди dependency-first. Зарегистрируй tools и MCP providers, создай или импортируй
knowledge packages, создай reusable templates, затем создай platform contracts,
которые композируют эти resources для конкретного project context.
```

## 4. Подключить Проект

```text
Подключи этот репозиторий к ProcessForge.

Сначала изучи структуру репозитория, выбери консервативный project type,
подключи его к существующему workplace, прочитай созданный
.pf/START_AGENT_HERE.md, запусти doctor-project, refresh project context и
кратко опиши, что ProcessForge теперь знает о проекте.
```

## 5. Собрать Platform Stack

```text
Собери project platform stack в ProcessForge.

Используй platform contracts как composition manifests. Если у stack есть
parent и child platform, опиши parent/child relationship в extends или
requires.platforms. Подключи knowledge packages, templates, tools, MCP
providers, capabilities, processes, coding standards и project type hints по id.
Запусти platform doctor и затем refresh project context snapshot.
```

## 6. Начать Run

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

## 7. Создать Собственный Process

```text
Создай новый ProcessForge process.

Используй process authoring flow, а не ручное написание YAML первым шагом.
Спроси цель процесса, stages, roles, gates, artifacts, нужные знания и
ожидаемый task loop. Проверь draft, примени его и проверь итоговый process.
```

## 8. Использовать Subagents

```text
Спланируй ProcessForge-assisted multi-agent run.

Используй встроенный multi-agent orchestration flow. Создай и проверь
orchestrator task plan, примени его для создания worker assignments и capsules,
запусти каждого worker только с его worker launch prompt и сведи outputs в
integration report перед delivery.
```

## 9. Agent Ledger И Process Handoffs

```text
Спланируй ProcessForge handoff с agent attendance tracking.

Зарегистрируй workplace agents, отметь check-in для нужных roles, создай или
проверь .pf/process-routes.yaml, создай handoff package, запусти
agent-director-tick для выдачи leases, если нужная role online, и возвращай
только конкретные expected artifacts.
```

## 10. Проверить Перед Delivery

```text
Проверь репозиторий перед delivery.

Используй ProcessForge release и validation runbook для агентов. Запусти нужные
проверки, пересобери release archive с нейтральным именем, проверь архив и
сообщи точные pass/fail evidence перед commit или push.
```

## Обязательный Порядок

## 11. Runtime Driver And Execution Inspector Smoke

```text
Используй ProcessForge runtime drivers для ограниченного execution-inspected test run.

Проверь built-in neutral runtime drivers, создай или используй orchestrator
plan с runtime.default_driver = test-echo-worker, запусти Process Execution
Inspector на малое число ticks и сообщи worker-run status files и produced
reports. Совместимые технические команды: `supervisor tick` и `supervisor run`;
более ясные aliases: `execution-inspector-tick` и `execution-inspector-run`.
```

1. Install ProcessForge distribution.
2. Verify ProcessForge itself.
3. Initialize workplace.
4. Configure path constants and roots.
5. Configure knowledge roots.
6. Register tools and MCP servers.
7. Create/import knowledge packages.
8. Create reusable templates.
9. Create platform contracts.
10. Onboard project.
11. Create run/task workflow.
12. Create custom processes as needed.

Capabilities описывают нужные действия, knowledge packages - где читать
правила, а platform contracts собирают application/domain stacks для проектов.
Base technologies являются knowledge packages и capabilities, а не platform
contracts.

Ядро ProcessForge domain-agnostic. Platforms, inheritance, package dependencies
и detection rules приходят из manifests и policy data.

Не копируйте весь репозиторий ProcessForge в `.codex`, `.claude`, `.agents` или
похожие папки конфигурации агентов. Установите ProcessForge один раз как
инструмент и укажите агенту, где он установлен; проектные инструкции находятся
в `.pf/START_AGENT_HERE.md`.
