# Журнал MCP remediation

## 2026-08-31T08:15:00+04:00 — codex-main / developer

- Область: `tools/pf_runtime/mcp_server.py` и focused smoke.
- Изменение: `missing_session` направляет в Garage либо к оператору и не
  предлагает агенту установку hooks.
- Проверка: `tools/smoke_mcp_missing_session_diagnostics.py`.
- Остаточный риск: real hosted Codex MCP acceptance зависит от доступности
  host-loaded MCP в assurance-среде.
