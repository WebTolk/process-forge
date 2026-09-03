# Baseline audit (pf-machine-baseline-audit-20260829)

## 1) Текущее состояние контейнера

### Источники конфигурации
- `project_root`: `D:\Dev\process-forge`
- `workplace`: `D:\.agents\processforge-workplace\workplace.yaml` (`.pf/process-forge.local.yaml`)
- `process-forge`: версия `1.1.0`, `install_mode: linked`, `mode: file_only`
- `process_forge`: `runner_required: false`, `backend_required: false`

### Состояние назначения
- Текущая задача: `pf-machine-baseline-audit-20260829`
- Run ID: `pf-machine-acceptance-20260829`, attempt `2`
- Предыдущий статус (`.pf/assignments/...yaml`): `failed` с ошибкой `WinError 2` (не найден файл)
- Текущий статус запуска (`.pf/runtime/.../status.json`): `running` (pid `10640`, heartbeat до `07:02:36Z`)

### Runtime
- Присвоенный драйвер: `codex-exec`
- Контрольная цепочка есть: `command.json`, `process.json`, `status.json`, `stdout.log`, `stderr.log`, `heartbeat.json`
- `heartbeat.json`: `status: starting`, `workspace_dirs: []` (текущий run не зафиксировал рабочие директории)
- Присутствует файл `workspace-access.json` с пустыми grants (`knowledge_resources/tools/mcp/templates: []`)
- Логи stdout уже содержат диагностический поток `agent.command.completed` (много вызовов) + явную аварийную запись:

  - `codex` worker попытка создать отчет завершилась с ошибкой и текстом:
    `Не удалось создать базовый baseline ...: состояние .pf, файл директория/права, workplace ...`
  - Повторяющиеся ошибки `rmcp::transport::worker` (HTTP stream 127.0.0.1:64442) и `failed to refresh available models`

## 2) Блокеры (до любых изменений)

### Критические
1. **Сбой предыдущей попытки из-за отсутствующего пути/файла (`WinError 2`)**
   Причина уже зафиксирована в assignment result summary.
2. **Разрыв telemtry по назначению в контракте**
   `.pf/runtime/telemetry/pf-machine-baseline-audit-20260829.ndjson` отсутствует (проверка чтения → `PathNotFound`).
3. **Нестабильная инициализация runtime-компонентов MCP-модели**
   В логах `rmcp` именные transport ошибки (`stream` endpoint не доступен), что может блокировать корректный ход baseline-итерации.

### Ограничения состояния
4. **Неполная/пустая выдача runtime workspace dirs в heartbeat** (`[]`) усложняет точную трассировку окружения в ходе сбора baseline.
5. **MCP/инструменты в этой задаче не выделены**
   requested/granted: `0`/`[]`; это ожидаемо по контракту, но означает, что любые проверки, требующие MCP, будут ограничены.

## 3) Срез по состоянию по направлениям запроса

- **Installed**: PF runtime и workflow конфигурированы, workplace подключен и доступен.
- **Source**: локальный источник проекта валиден (`D:\Dev\process-forge`), `install_mode` и `version` читаемы.
- **Workplace**: явно привязан к `D:\.agents\processforge-workplace\workplace.yaml`.
- **Runtime**: процессы и артефакты запуска присутствуют, но run в текущей попытке остаётся с симптомами стартового/неустойчивого состояния.
- **MCP**: не выделены ресурсы/модули в этой задаче; активные MCP-адреса не задействованы.

## 4) Рекомендуемый next step для продолжения
- Запустить повторную попытку baseline после явного контроля наличия файла, который падает под `WinError 2`, и проверки стабильности `codex-exec` transport (особенно локального `127.0.0.1:64442` для RMCP).