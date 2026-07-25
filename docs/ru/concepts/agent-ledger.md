# Agent Ledger

ProcessForge не является harness. Он фиксирует процессную обвязку вокруг harness, агентов и инструментов.

Agent ledger - это workplace-слой присутствия. Агенты регистрируются в `registries/agents.yaml`, приходят через `agent-checkin`, обновляют присутствие через `agent-heartbeat` и уходят через `agent-checkout`.

События пишутся в `runtime/agent-ledger/sessions.ndjson`. Текущее состояние лежит в `runtime/agent-presence/<agent-id>.json`. Lease в `runtime/agent-leases/<lease-id>.yaml` - это ключ, который выдаёт ограниченный доступ к задаче, capsule, run и файловому scope.
