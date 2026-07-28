# Модель агентской сессии

У ProcessForge есть два понятных человеку режима работы.

Первый режим - гараж с инструментами. Это `1-1-1-1`: один человек-оператор,
одна основная агентская сессия, один проект и один активный process или run.
Такой режим подходит для большинства обычных задач: агент последовательно ведёт
работу, берёт нужные инструменты и знания из workplace, пишет артефакты,
запускает проверки и завершает сессию. Director не требуется, а Worker и
Inspector остаются ролями или фазами той же сессии.

Шаблон промпта для режима гаража:

```text
Инициализируй проект по ProcessForge, подключи все необходимые инструменты и
знания, мы делаем <название того, что делаем>. Заполняй все требуемые артефакты.
```

Пример для разработки Joomla-плагина:

```text
Инициализируй проект по ProcessForge, подключи все необходимые инструменты и
знания для разработки Joomla-плагина. Мы делаем контентный плагин Joomla,
который добавляет AI-пояснение к материалам сайта. Заполняй все требуемые
артефакты, фиксируй решения по архитектуре, реализации, проверкам и поставке.
```

Второй режим - кузница или фабрика. В нём несколько агентов могут работать
параллельно: каждый получает изолированную задачу, Agent Director координирует
маршруты и передачи, Agent Ledger ведёт журнал вахтёра, а handoffs и process
transitions передают результаты между участниками и процессами. Этот режим
нужен для сложных процессов: ветвления, запуска дочернего процесса, возврата в
родительский процесс с результатом, внешних runtime workers и проверяемой
параллельной работы.

Primary Agent Session, или основная агентская сессия, - это один запуск агента
в одном проекте по одному активному process/run. В simple mode этот агент
последовательно ведет процесс, запускает CLI checks, проходит gates, пишет
артефакты, отчёты и handoffs, затем завершает сессию.

Presence record сессии включает `agent_id`, `session_id`, `project_root`
reference, optional `project_id`, `process_id`, optional `run_id`, `roles`,
`started_at`, `last_seen_at`, optional `finished_at` и `status`.

## Execution modes

`single_agent`: один primary agent последовательно выполняет процесс в одном
проекте. Это стандартный `.pf` сценарий, близкий к старому локальному
single-agent flow: один агент идёт по проектному процессу без обязательного
Director или Supervisor.

`single_agent_with_subagents`: один primary agent владеет процессом, но может
вызывать subagents для ограниченного анализа или проверок. Результат subagents
- отчёты и артефакты внутри текущего run; они не становятся workplace agents,
если отдельно не регистрируются и не делают check-in.

`orchestrated_agents`: Agent Director или Orchestrator координирует несколько
agent sessions. Каждый worker остается отдельной `1-1-1-1` сессией со своим
assignment, capsule, scope, `session_id` и lifecycle.

`process_factory`: несколько process runs связаны process routes, handoffs и
continuations. Director координирует передачи между процессами; каждый
исполнитель всё равно работает внутри agent session.

## Роли в single-agent mode

Operator ставит задачу и принимает результат.

Primary Agent владеет process/run, выполняет работу, запускает CLI checks,
пишет итерации, артефакты и финальный отчёт или handoff.

Worker не является отдельным участником. Это та же primary agent session в
фазе выполнения.

Inspector не является отдельным участником. Это CLI checks, process gates и
self-check того же primary agent.

Agent Ledger есть во всех режимах, но это файловый журнал вахтёра, которым
управляют CLI-команды, а не отдельный агент. Agents отмечаются в начале сессии,
отправляют heartbeat во время долгой работы и делают checkout перед уходом.

Agent Director не нужен в single-agent mode. Process Supervisor / Execution
Inspector не нужен, пока процесс не запускает внешних runtime workers.

Простые single-agent sessions в MVP не требуют явной ручной lease. Explicit
leases используются для multi-agent, handoff и runtime-worker сценариев.

## Agent id и session id

`agent_id` отвечает на вопрос, кто это. `session_id` отвечает на вопрос, какой
конкретный приход/запуск/окно/проект сейчас активен.

Один `agent_id` может иметь несколько активных `session_id`, например два окна
терминала с двумя проектами. Session-safe presence хранится здесь:

```text
<workplace>/runtime/agent-presence/<agent-id>/<session-id>.json
```

Project-local ссылка на текущую сессию хранится здесь:

```text
.pf/runtime/current-session.json
```

Эти файлы среды выполнения приватные и не входят в публичный релизный архив.

## Session commands

Можно использовать ledger command names или простые aliases:

```bash
python bin/pf.py session-start --workplace <workplace> --project-root <project> --agent primary-agent --process task-batch-execution
python bin/pf.py session-heartbeat --project-root <project>
python bin/pf.py session-status --project-root <project> --json
python bin/pf.py session-end --project-root <project>
```

Aliases являются thin wrappers над `agent-checkin`, `agent-heartbeat`,
`agent-status` и `agent-checkout`.
