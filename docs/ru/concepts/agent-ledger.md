# Agent ledger

ProcessForge не является harness. Он фиксирует процессную обвязку вокруг harness, агентов и инструментов.

Agent ledger - это workplace-слой присутствия и сессий. Это не отдельный
агент. Agents регистрируются в `registries/agents.yaml`, приходят через
`agent-checkin` или `session-start`, обновляют presence через
`agent-heartbeat` или `session-heartbeat` и уходят через `agent-checkout` или
`session-end`.

События пишутся в `runtime/agent-ledger/sessions.ndjson`. Текущее состояние
хранится по сессиям:
`runtime/agent-presence/<agent-id>/<session-id>.json`, поэтому один `agent_id`
может иметь несколько активных sessions в разных проектах или окнах терминала.
Lease в `runtime/agent-leases/<lease-id>.yaml` - это ключ, который выдаёт
ограниченный доступ к задаче, capsule, run и файловому scope.

Ledger записывает явку, presence, stale/offline status и lifecycle leases. Он
не думает, не принимает решений, не выбирает process routes, не принимает и не
финализирует handoffs, не запускает worker processes и не проверяет task
outputs. Director читает ledger state для координации, а Execution Inspector
читает task/runtime state для проверки исполнения. См.
[Модель агентской сессии](agent-session-model.md) и
[Граница Director, Ledger, Inspector и Worker](director-ledger-inspector-boundary.md).
