# Agent director

Agent Director - это процесс и CLI-слой ProcessForge. Это не WT AICC и не web UI.

Agent Director не нужен для стандартного single-agent режима `1-1-1-1`. Такой
режим похож на гараж с инструментами: один оператор, одна primary agent session,
один project и один process/run. Director появляется, когда ProcessForge
собирает несколько agent sessions или несколько process runs через routes,
handoffs, leases и continuations.

Director process работает в границах workplace. Director-capable workplace
может одновременно содержать проекты, где только часть имеет effective
`organized` mode; явные `simple` projects по умолчанию не получают Director
cases и inbox obligations. Перед маршрутизацией проекта к Director используйте
`project-mode status`.

`agent-director-tick` выполняет один детерминированный проход: смотрит pending
handoffs, проверяет доступность агентов, выдаёт leases, переводит handoff в
`ready`, оставляет `waiting_for_agent`, если нужной роли нет, и помечает
просроченные leases как `stale`.

Director использует workplace ledger и presence-файлы. Он не запускает worker
runtime processes, не пишет `.pf/runtime/agent-runs/**/process.json`,
`heartbeat.json` или `exit.json` и не выводит успех task из одного report
artifact. Когда нужно состояние выполнения, Director обращается к Process
Execution Inspector через `execution-inspector-status`,
`execution-inspector-tick`, `execution-inspector-run` или совместимые команды
`supervisor`.

В public tests Director не запускает реальные внешние agent CLI. См.
[Граница Director, Ledger, Inspector и Worker](director-ledger-inspector-boundary.md).
