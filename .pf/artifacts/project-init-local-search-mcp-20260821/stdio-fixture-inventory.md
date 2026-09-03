# stdio-fixture-inventory

## Цель
- Получить воспроизводимый стенд для проверки `stdio` MCP: `initialize` → `tools/list` → `tools/call` с ошибкой `session_project_mismatch` на чужом проекте.
- Проект/сессия должны быть привязаны в Ledger через `agent-checkin` (через `project-onboard` + `project-root`).

## Минимальная фикстура
- `WORKPLACE` — временная workplace.
- `P1` — Ledger-проект, с которым привязывается сессия.
- `P2` — второй онборженный проект, который используется как «чужой».
- `SESSION_ID` — фиксированный id сессии, передаваемый в MCP.

## Шаги (Windows PowerShell)

```powershell
$root = Join-Path $env:TEMP "pf-mcp-stdio-fixture"
$workplace = Join-Path $root "workplace"
$p1 = Join-Path $root "proj-a"
$p2 = Join-Path $root "proj-b"
$sessionId = "fixture-session-stdio-20260821"
$agentId = "fixture-agent-stdio"

New-Item -ItemType Directory -Path $workplace, $p1, $p2 -Force | Out-Null

# 1) bootstrap workplace
python tools/processforge.py workplace-init --workplace $workplace --apply

# 2) onboard 2 временных проекта
python tools/processforge.py project-onboard --project-root $p1 --workplace $workplace --type generic --apply
python tools/processforge.py project-onboard --project-root $p2 --workplace $workplace --type generic --apply

# 3) создать агента (по желанию) и зафиксировать session в Ledger на P1
python tools/processforge.py agent-register --workplace $workplace --agent $agentId --role worker --kind operator_started_agent --apply
python tools/processforge.py agent-checkin --workplace $workplace --agent $agentId --session $sessionId --project-root $p1 --role worker

# 4) прогнать MCP и зафиксировать 3 запроса
$mcp = @"
{"jsonrpc":"2.0","id":1,"method":"initialize"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"pf.project_initialization.status","arguments":{"session_id":"$sessionId","project_root":"$p2"}}}
"@

$mcp | python tools/pf_runtime/mcp_server.py --workplace $workplace --session $sessionId
```

## Что должны вернуть ответы
- Для `id=1`:
  - `result.protocolVersion == "2024-11-05"`.
  - `result.serverInfo.name == "processforge"`.
- Для `id=2`:
  - список содержит минимум 9 инструментов (в т.ч. `pf.project_state`, `pf.project_initialization.status`, `pf.work_state`, `pf.resolve`, `pf.search`, `pf.workplace_state`, `pf.session_context`, `pf.session_chat`, `pf.session_activity`).
- Для `id=3` (чужой проект):
  - `isError == true`.
  - `result.content[0].text` после `ConvertFrom-Json` содержит `{"error":{"code":"session_project_mismatch"}}`.

## Проверка корректной привязки (бонус-assert)
- Для контроля используйте один и тот же `session_id` с `project_root == "$p1"`:
  - `tools/call` должен вернуть `result.content[0].text` без `error`.

## Очистка
```powershell
Remove-Item -Recurse -Force $root
```

