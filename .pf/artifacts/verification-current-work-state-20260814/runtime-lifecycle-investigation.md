# Runtime lifecycle investigation

## 1) Результат (диагностика из фактов)

Проверка воспроизводимо подтверждает расхождение между `runtime start` и `runtime stop` для `long-lived runtime`:

- Запуск дал валидный ответ CLI: `pid=13064`, `status=started`, `endpoint=...`.
- После запуска `runtime session-register ...` и `runtime work-state ...` возвращает `FAIL: runtime is not running`, хотя `runtime status` показывает:
  - `status: stale`
  - `health: stale`
  - `pid: 13064`
  - `endpoint: http://127.0.0.1:50295`
- После `runtime stop` статус процесса из `Get-Process -Id 13064` остаётся живым.
- Далее `runtime stop` (`RUNTIME: not running`) не устраняет сохранённый `pid/endpoint` и статус остаётся персистентно `stale`.

То есть наблюдается «живой PID в стате, но управляемый runtime-инстанс не отвечает как живой сервис», и stop-команда не делает корректный флаш/переинициализацию state файла.

## 2) Точный кодовый путь и файлы состояния

### 2.1 Команды CLI и точка истины состояния
- Долгоживущий runtime (`runtime`) работает через артефакты в `.pf/runtime/pf-runtime`:
  - `service.json` (оперативный статус runtime, pid, endpoint, health/status).
  - `runtime.lock` (идентификатор инстанса/PID для singleton/recovery).
- В smoke-скрипте это зафиксировано напрямую:
  - `[tools/smoke_long_lived_runtime.py](D:/Dev/process-forge/tools/smoke_long_lived_runtime.py)`:
    - `runtime_dir()` → `runtime/pf-runtime`
    - чтение `service.json` в `service_state()`
    - запись `runtime.lock`/`service.json` и проверка сценариев orphan-start/recovery.
- Процесс-уровень `runtime-host` использует отдельный state:
  - `[tools/pf_runtime/host.py](D:/Dev/process-forge/tools/pf_runtime/host.py)`:
    - `state_path() -> workplace/runtime/pf-runtime-host/state.json` (кэш сессий/проектов для host-интерфейсов).

### 2.2. MCP и ledger hooks
- `[tools/smoke_runtime_ledger_hooks_mcp.py](D:/Dev/process-forge/tools/smoke_runtime_ledger_hooks_mcp.py)` подтверждает, что runtime CLI для MCP/adapter использует тот же `runtime/pf-runtime/service.json` и endpoint как source of truth.

### 2.3. Несоответствие ожидаемого источника статуса
- `.pf/artifacts/verification-current-work-state-20260814/live-runtime-mcp-proof.md` указывает попытку чтения `.pf/runtime/pf-runtime/status.json`, но в репозитории для runtime используется `service.json`, поэтому это уже сам по себе признак разнобоя в документации/используемом пути при расследовании.

## 3) Наиболее вероятная причина

Разбор симптомов указывает на «небезопасный stop/cleanup при частично живом/стёртом singleton»:

- `stop` инициализируется как будто runtime «не запущен», не валидируя надёжно, что PID в `service.json` принадлежит корректно запущенному runtime-серверу (или не выполняя принудительное снятие stale-статуса).
- `start` пишет новый PID/endpoint в persist-state, но не добивает состояние до `ready` или не синхронизирует его с фактической доступностью сервиса.
- Итог: CLI-уровень держит stale-состояние с `pid/endpoint`, в то время как service route фактически недоступен для session ingress.

## 4) Минимальная безопасная ремедиация (без изменения доменной логики)

Предпочтительно точечно в runtime lifecycle-команде (стоп/старта/читателя статуса):

1. На `runtime status` считать `service.json` как кандидата статуса, но признавать его недействительным, если:
   - PID отсутствует/невалиден, или
   - `os.kill(pid, 0)` (или аналог) не подтверждает процесс, или
   - endpoint недоступен heartbeat/health в течение короткого окна.
2. На `runtime stop`:
   - Если PID есть, но процесс не совпадает с ожидаемым runtime (или не откликается как runtime endpoint), обязательно выполнить **чистку stale state**:
     - удалить/переписать `service.json` в консистентное `stopped`,
     - удалить `runtime.lock`,
     - вернуть `status=stopped` (без ложного `not running`).
3. На `runtime start` перед spawn:
   - если обнаружен stale singleton (lock/pid mismatch или unreachable endpoint), принудительно очистить runtime state и инициализировать новый lock/instance-id до старта сервиса.
4. Для `session-register/work-state` при получении stale-состояния возвращать диагностический код/сообщение о необходимости `runtime stop --force` или `runtime start --recover`, а не просто `runtime is not running`.

Это минимально и сохраняет контракт стабильного singleton/чистоты state, закрывая разрыв между persisted state и фактической жизнью процесса.

## 5) Риски и остатки

- `runtime stop` на текущей реализации не является идемпотентным относительно stale singleton; есть риск повторных ложных `not running` при частичной деградации процесса.
- `session-register`/`work-state` зависят от корректности service-state; при расхождении наблюдается ложная недоступность runtime.
- По задаче изменения кода не выполнялись (режим `code_changes_allowed: false`), подготовлен только план безопасного исправления.