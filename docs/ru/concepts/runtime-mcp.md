# MCP facade PF Runtime

`tools/pf_runtime/mcp_server.py` — минимальный read-only stdio MCP-сервер. Он
требует уже существующую identity session из Agent Ledger (`--session` либо
`PF_MCP_SESSION_ID`) и не создаёт отдельную привязку MCP к проекту.

Доступны `pf.project_state`, `pf.work_state`, `pf.resolve` и
`pf.workplace_state`. `pf.resolve` читает метаданные выбранного ресурса из
resolved context текущего проекта, не заставляя агента искать workplace вручную.

`pf.work_state` также возвращает summary декларативных technical projections
Ledger-bound проекта. Это read-only view generated-артефакта
`stage-obligations`: MCP не создаёт вторую project binding и не записывает
projection state.
