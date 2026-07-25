# Agent Director

Agent Director - это процесс и CLI-слой ProcessForge. Это не WT AICC и не web UI.

`agent-director-tick` выполняет один детерминированный проход: смотрит pending handoffs, проверяет agent availability, выдаёт leases, переводит handoff в `ready`, оставляет `waiting_for_agent`, если нужной роли нет, и помечает просроченные leases как `stale`.

Director использует workplace ledger и presence-файлы. В public tests он не запускает реальные внешние agent CLI.
