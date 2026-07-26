# Agent Director

Agent Director - это процесс и CLI-слой ProcessForge. Это не WT AICC и не web UI.

Agent Director не нужен для стандартного single-agent `1-1-1-1` flow. Такой
flow состоит из одного operator, одной primary agent session, одного project и
одного process/run. Director появляется, когда ProcessForge композирует
несколько agent sessions или несколько process runs через routes, handoffs,
leases и continuations.

`agent-director-tick` выполняет один детерминированный проход: смотрит pending handoffs, проверяет agent availability, выдаёт leases, переводит handoff в `ready`, оставляет `waiting_for_agent`, если нужной роли нет, и помечает просроченные leases как `stale`.

Director использует workplace ledger и presence-файлы. Он не запускает worker
runtime processes, не пишет `.pf/runtime/agent-runs/**/process.json`,
`heartbeat.json` или `exit.json` и не выводит успех task из одного report
artifact. Когда нужно execution state, Director обращается к Process Execution
Inspector через `execution-inspector-status`, `execution-inspector-tick`,
`execution-inspector-run` или совместимые `supervisor` commands.

В public tests Director не запускает реальные внешние agent CLI. См.
[Граница Director, Ledger, Inspector и Worker](director-ledger-inspector-boundary.md).
