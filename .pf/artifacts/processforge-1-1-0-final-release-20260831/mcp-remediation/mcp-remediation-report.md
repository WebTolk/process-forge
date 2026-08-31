# MCP missing-session remediation

`missing_session` больше не предлагает обычному проектному агенту установить
Codex hooks. Ответ указывает на доступные Garage tools, а для Forge-only view
возвращает явное `operator_action: verify_host_session_integration`.

Низкоуровневый `install_codex_hooks` сохранён в схеме явного
`pf.project_initialization.repair`: это операторская opt-in возможность, а не
автоматический repair project readiness.
