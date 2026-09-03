# Acceptance: hosted Codex MCP

## Подтверждено локально

- `smoke_mcp_codex_contract` — PASS.
- `smoke_runtime_mcp_autostart` — PASS.
- `smoke_project_init_local_search_mcp` — PASS.
- Garage sessionless и session-enhanced MCP paths — PASS.
- `missing_session` направляет обычную работу в Garage, а Forge-only failure —
  к оператору; `install_codex_hooks` не предлагается как agent repair.
- Документация фиксирует host-owned stdio lifecycle: MCP не является detached
  daemon и не регистрируется в Windows autostart.

## Внешняя граница доказательства

В текущем Codex-сеансе PF MCP tools не загружены как callable host tools,
поэтому реальный вызов через уже зарегистрированный Codex MCP host не может
быть честно отмечен PASS. Direct stdio smoke не подменяет это доказательство.
Перед публичным выпуском оператор должен открыть свежий Codex host session с
установленной MCP-регистрацией и вызвать как минимум `pf.context` и
`pf.work.start` на тестовом проекте.
