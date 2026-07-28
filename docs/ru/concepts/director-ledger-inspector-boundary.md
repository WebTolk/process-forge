# Граница Director, Ledger, Inspector и worker

ProcessForge разделяет координацию агентов и проверку выполнения.
`supervisor` остается историческим техническим именем CLI, но по смыслу эта
роль называется Process Execution Inspector.

Эти роли не являются обязательными участниками стандартного single-agent режима.
В режиме гаража с инструментами работают один оператор, одна primary agent
session, один project и один process/run. Worker в этом режиме - тот же primary
agent в фазе выполнения, а Inspector - CLI checks, gates и self-check. См.
[Модель агентской сессии](agent-session-model.md).

| Responsibility | Ledger | Director | Inspector | Worker |
| --- | --- | --- | --- | --- |
| agent check-in/check-out | yes | no | no | no |
| presence/stale status | yes | reads | no | no |
| grant/revoke lease | no | yes | no | no |
| process route decision | no | yes | no | no |
| handoff accept/return/finalize | no | yes | no | no |
| start/check worker process | no | may ask | yes | no |
| heartbeat/exit/status observation | no | reads | yes | writes |
| required output validation | no | reads | yes | writes |
| perform task | no | no | no | yes |

## Роли

Agent Ledger - это журнал вахтёра для workplace. Он записывает check-in,
check-out, текущую явку, stale/offline status и lifecycle leases.

Agent Director - координатор. Он читает ledger presence, выбирает process
routes, выдает или отзывает leases, переводит handoffs между состояниями и
готовит continuation work. Director может спросить Execution Inspector о
состоянии выполнения, но не должен запускать shell worker processes или считать
задачу успешной только по наличию report artifact.

Process Execution Inspector - проверяющий выполнение. Совместимые CLI-имена:
`supervisor`, `supervisor-tick`, `supervisor-run`, `supervisor-status` и
`supervisor-stop`; более ясные aliases: `execution-inspector-tick`,
`execution-inspector-run`, `execution-inspector-status` и
`execution-inspector-stop`. Эта роль смотрит assigned task state, запускает
разрешённые runtime drivers, если это настроено, проверяет process, heartbeat,
exit proof, required outputs и expected reports, затем помечает tasks как done
или failed.

Worker Agent выполняет одну назначенную capsule task и пишет ожидаемые outputs
и runtime proof, которые требует driver.

## Правила границы

Supervisor / Execution Inspector не должен выдавать leases, писать workplace
agent ledger events, принимать или финализировать handoffs, выбирать routes,
назначать agents или решать ownership project/run.

Director не должен напрямую запускать worker runtime processes, писать
`.pf/runtime/agent-runs/**/process.json`, `heartbeat.json`, `exit.json` или
выводить успех task из одного report artifact. Когда важно состояние выполнения, он
должен обращаться к CLI инспектора.
