# Agent ledger

ProcessForge не является harness. Он фиксирует процессную обвязку вокруг harness, агентов и инструментов.

Agent ledger - это workplace-слой присутствия и сессий. Это не отдельный
агент. В Forge/фабрике штатный путь — автоматическая доставка lifecycle и
активности через поддерживаемые хуки Codex/Kimi → Host → Ledger. Новый
допущенный prompt, compaction и tool activity обновляют точную авторизованную
сессию без периодических вызовов LLM. Явные CLI/MCP операции `agent-heartbeat`
и `session-heartbeat` остаются ручным совместимым API; `agent-checkin` /
`session-start` и `agent-checkout` / `session-end` доступны оператору.

Допуск сохраняет проверки registry, provenance, project и владельца session.
Неизвестный/raw-only, отклонённый, повторный или replay input не обновляет
presence; активность не открывает завершённую сессию и не продлевает lease.
Отключение raw hook history не выключает поддерживаемую нормализованную доставку.
Во время молчания heartbeat не синтезируется. Активность сессии отделена от
execution receipts и доказательств владения OS process/tree или завершения.

Локальный Garage не требует Runtime, hooks или Ledger. Автоматическая доставка
зависит от фактической регистрации хуков провайдера и конфигурации Host;
поведение исходников само по себе не подтверждает регистрацию или пригодность
конкретного устройства.

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

Ledger относится к workplace, но не заменяет Raw Event Journal. Raw ingress
может создать производный session/telemetry effect только после проверки scope;
Ledger не хранит копию каждого raw payload.
