# Live Runtime / MCP proof

Дата проверки: `2026-08-14`
Режим: `read-only`, без изменений исходников.

## Что подтверждено

### 1. Живой CLI/runtime-host путь для новой декларативной проекции работает

Команды и наблюдения:

```text
python tools/processforge.py runtime-host projection-doctor --project-root .
```

Сначала вернул:

```text
FAIL: process-forge stage obligations projection has missing required output
```

Затем:

```text
python tools/processforge.py runtime-host rebuild-projections --project-root . --json
```

Вывел путь к пересобранным артефактам:

```json
{
  "projections": [
    {
      "project_id": "process-forge",
      "projection": ".pf/artifacts/projections/command-history.md",
      "stage_projection": ".pf/artifacts/projections/stage-obligations.json"
    }
  ]
}
```

После пересборки повторная проверка:

```text
python tools/processforge.py runtime-host projection-doctor --project-root .
```

Вернула:

```text
PASS: process-forge stage obligations projection is current
```

Это подтверждает live-путь:
- декларативная проекция `stage-obligations` реально читается/валидируется;
- `projection-doctor` живёт на текущем checkout, а не только в unit/smoke-логике;
- rebuild переводит проекцию в согласованное текущее состояние.

### 2. MCP-подобные read-only surfaces читаются с текущего проекта

Команда:

```text
python tools/processforge.py runtime-host work-state --workplace . --project-root . --json
```

Вернула рабочее состояние проекта `process-forge`, включая:

- `project.project_id = "process-forge"`
- `events_path = ".pf/runtime/events/events.ndjson"`
- `event_count = 1366`
- `projections.stage_obligations.status = "current"`
- `current_work_state.freshness = "current"`
- `current_work_state.technical_obligations = []`
- `current_work_state.blockers = []`

Команда:

```text
python tools/processforge.py runtime-host project-state --workplace . --project-root . --json
```

Вернула:

- `project.project_id = "process-forge"`
- `effective_mode = "simple"`
- `context_status = "stale"`

Это и есть подтверждённый read-only MCP-like слой:
- `project-state`
- `work-state`

Они читаются на живом checkout без правок кода.

## Что подтверждено частично

### 3. Long-lived `runtime` стартует, но не доходит до рабочего состояния для session ingress

Команда запуска:

```text
python tools/processforge.py runtime start --workplace . --json
```

Вернула:

```json
{
  "endpoint": "http://127.0.0.1:50295",
  "pid": 13064,
  "status": "started"
}
```

Сразу после этого команды ingress/read через long-lived runtime:

```text
python tools/processforge.py runtime session-register --workplace . --session live-runtime-proof-20260814 --agent codex --project-root . --json
python tools/processforge.py runtime work-state --workplace . --session live-runtime-proof-20260814 --json
```

обе вернули:

```text
FAIL: runtime is not running
```

При этом статус runtime показывал не `stopped`, а зависшее состояние:

```text
python tools/processforge.py runtime status --workplace . --json
```

Наблюдаемое состояние:

- `status = "stale"`
- `health = "stale"`
- `pid = 13064`
- `endpoint = "http://127.0.0.1:50295"`
- `updated_at` менялся
- scheduler jobs (`director`, `inspector`, `ledger`, `projection`) продолжали обновлять `last_run`

То есть live long-lived runtime:
- формально стартует;
- оставляет PID;
- пишет stale-status;
- но не принимает последующий `session-register`/`work-state` как running service.

### 4. Останов long-lived runtime через CLI не подтвердился

Команда:

```text
python tools/processforge.py runtime stop --workplace .
```

Вернула:

```text
RUNTIME: not running
```

Но сразу перед ручным завершением:

```text
Get-Process -Id 13064
```

подтвердил, что PID `13064` ещё существовал.

Для очистки после проверки процесс был завершён вручную:

```text
Stop-Process -Id 13064
```

После этого `Get-Process -Id 13064` процесс уже не находил, но:

```text
python tools/processforge.py runtime status --workplace . --json
```

всё ещё показывал stale state с тем же PID и endpoint. Это выглядит как рассинхрон между фактическим процессом и persisted runtime status.

## Блокеры и границы доказательства

### 5. Прямой Codex hook adapter / настоящий MCP ingress не подтверждён

В этом worker assignment отсутствовал доступ к MCP/tool surface:

- `workspace_access.mcp = 0`
- `workspace_access.tools = 0`

Поэтому прямой вызов установленного Codex hook adapter в рамках капсулы не был доступен.
Подтверждён только ручной CLI/read-only путь:

- `runtime-host project-state`
- `runtime-host work-state`
- `runtime-host projection-doctor`
- `runtime-host rebuild-projections`

Именно это нужно отделять от hook/MCP ingress: проблема адаптера/доступа не отменяет подтверждённый CLI/runtime-host proof.

### 6. Изолированный smoke для новой логики не выполнился из-за ограничений среды, а не из-за бизнес-логики

Команда:

```text
python tools/smoke_verification_current_work_state.py
```

упала на первом `init-workplace` во временном каталоге `D:\Temp\pf-verification-state-*` с `PermissionError [WinError 5]`.
Это блок среды выполнения на создание временного workplace, а не доказанный дефект `verification-state/current-work-state`.

## Итог

Подтверждено:

- новая declaration-driven проекция `verification-state`/`stage-obligations` реально участвует в live `runtime-host projection-doctor`;
- live rebuild-путь существует и переводит проекцию в `current`;
- read-only MCP-like surfaces `runtime-host project-state` и `runtime-host work-state` работают на текущем checkout.

Не подтверждено до конца:

- стабильный long-lived `runtime` ingress через `session-register`/`work-state`;
- корректный CLI stop для long-lived runtime;
- прямой Codex hook adapter / настоящий MCP session ingress из этой worker-капсулы.

Главный практический вывод: CLI/runtime-host доказательство новой декларативной state-модели есть; блок находится в long-lived runtime/session ingress слое и в отсутствии доступного hook/MCP adapter surface для этого worker-запуска.