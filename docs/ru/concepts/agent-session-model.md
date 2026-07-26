# Модель Агентской Сессии

Атомарная единица выполнения ProcessForge - `1-1-1-1`:

- 1 человек-оператор
- 1 основная агентская сессия
- 1 проект
- 1 активный process или run

Primary Agent Session, или основная агентская сессия, - это один запуск агента
в одном проекте по одному активному process/run. В simple mode этот агент
последовательно ведет процесс, запускает CLI checks, проходит gates, пишет
artifacts/reports/handoffs и завершает сессию.

Presence record сессии включает `agent_id`, `session_id`, `project_root`
reference, optional `project_id`, `process_id`, optional `run_id`, `roles`,
`started_at`, `last_seen_at`, optional `finished_at` и `status`.

## Execution Modes

`single_agent`: один primary agent последовательно выполняет процесс в одном
проекте. Это стандартный `.pf` flow, близкий к старому локальному single-agent flow: один
агент идет по проектному процессу без обязательного Director или Supervisor.

`single_agent_with_subagents`: один primary agent владеет процессом, но может
вызывать subagents для ограниченного анализа или проверок. Результат subagents
- reports/artifacts внутри текущего run; они не становятся workplace agents,
если отдельно не регистрируются и не делают check-in.

`orchestrated_agents`: Agent Director или Orchestrator координирует несколько
agent sessions. Каждый worker остается отдельной `1-1-1-1` сессией со своим
assignment, capsule, scope, `session_id` и lifecycle.

`process_factory`: несколько process runs связаны process routes, handoffs и
continuations. Director координирует передачи между процессами; каждый
исполнитель все равно работает внутри agent session.

## Роли В Single-Agent Mode

Operator ставит задачу и принимает результат.

Primary Agent владеет process/run, выполняет работу, запускает CLI checks,
пишет iterations, artifacts и финальный report/handoff.

Worker не является отдельным участником. Это та же primary agent session в
фазе выполнения.

Inspector не является отдельным участником. Это CLI checks, process gates и
self-check того же primary agent.

Agent Ledger есть во всех режимах, но это CLI-managed файловый журнал, а не
отдельный агент-вахтер. Agents отмечаются в начале сессии, отправляют
heartbeat во время долгой работы и делают checkout перед уходом.

Agent Director не нужен в single-agent mode. Process Supervisor / Execution
Inspector не нужен, пока процесс не запускает внешних runtime workers.

Простые single-agent sessions в MVP не требуют явной ручной lease. Explicit
leases используются для multi-agent, handoff и runtime-worker сценариев.

## Agent Id И Session Id

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

Эти runtime files приватные и не входят в public release archive.

## Session Commands

Можно использовать ledger command names или простые aliases:

```bash
python bin/pf.py session-start --workplace <workplace> --project-root <project> --agent primary-agent --process task-batch-execution
python bin/pf.py session-heartbeat --project-root <project>
python bin/pf.py session-status --project-root <project> --json
python bin/pf.py session-end --project-root <project>
```

Aliases являются thin wrappers над `agent-checkin`, `agent-heartbeat`,
`agent-status` и `agent-checkout`.
