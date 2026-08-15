# Отчёт: write-worker-runtime-diagnosis (`central-ingress-write-runtime-diagnosis-20260814`)

## 1) Что проверено
- Wrapper для write-воркера:
  - `.pf/tmp/codex_workspace_write_worker.py`
  - `.pf/tmp/codex_workspace_write_worker.cmd`
- Записи запуска и состояния трёх воркеров в:
  - `.../central-ingress-core-storage-implementation-20260814/*.json|*.log`
  - `.../central-ingress-first-slice-implementation-20260814/*.json|*.log`
  - `.../central-ingress-raw-kernel-implementation-20260814/*.json|*.log`
- Диагностический run для сопоставления:
  - `.../central-ingress-write-runtime-diagnosis-20260814/*`
- Сравнение с `stop requested` задачей, где heartbeat есть:
  - `.../central-ingress-current-state-audit-20260814/status.json` и `heartbeat.json`

## 2) Факты по трём остановленным воркерам
1. `central-ingress-first-slice-implementation-20260814`
   - `command.json`: `driver_id` = `generic-shell`, `executable` = `.pf\\tmp\\codex_workspace_write_worker.cmd`
   - `status.json`: `status=cancelled`, `failure_reason="stop requested"`, `started_at=null`, `exit_code=null`
   - `process.json`: `started_at` задан, `pid` есть
   - `heartbeat.json`: **нет файла**
   - `stdout.log`: пусто (0 строк)

2. `central-ingress-core-storage-implementation-20260814`
   - `command.json`: тот же `driver_id=generic-shell`, тот же `.cmd`
   - `status.json`: `status=cancelled`, `failure_reason="stop requested"`, `started_at=null`, `exit_code=null`
   - `process.json`: `started_at` задан, `pid` есть
   - `heartbeat.json`: **нет файла**
   - `stdout.log`: пусто (0 строк)

3. `central-ingress-raw-kernel-implementation-20260814`
   - `command.json`: тот же `driver_id=generic-shell`, тот же `.cmd`
   - `status.json`: `status=cancelled`, `failure_reason="stop requested"`, `started_at=null`, `exit_code=null`
   - `process.json`: `started_at` задан, `pid` есть
   - `heartbeat.json`: **нет файла**
   - `stdout.log`: пусто (0 строк)

Дополнительно: во всех трёх `stderr.log` есть только диагностический шум старта/инициализации и RMCP-ошибки транспорта, но нет завершённых трассбеков о write-операциях; это согласуется с прерыванием до фактического старта логических шагов.

## 3) Вывод о причине
Причина безусловно не в анализе/выполнении изменений в коде воркера, а в **внешнем принудительном завершении раннера** на уровне runtime-управления:
- все три задачи помечены `failure_reason="stop requested"`,
- `status.started_at` пустой при наличии `process.started_at`, что типично для остановки после запуска процесса до завершения жизненного цикла,
- heartbeat файл не создан, следовательно, воркер не дошёл до стандартной точки публикации состояния прогресса/heartbeat.

Иными словами, источник «дошёл до анализ-состояния, но не написал ни код, ни heartbeat» — не ошибка анализа, а `worker` lifecycle control, триггерющий ранний `cancel`.

## 4) Рекомендуемое минимальное безопасное изменение

### Проектно-локальный workaround (без изменения установленного дистрибутива)
- Для проблемных write-вставить переход на `codex-exec` драйвер (как в диагностической/`current-state-audit` задаче): запуск через `codex_exec_worker.py` с `--output` и `--heartbeat` напрямую, без промежуточного `generic-shell` cmd-обёртки.
- В задачах этого run’а зафиксировать `runtime driver` явно и зафиксировать параметры heartbeat на уровне запуска, чтобы избежать гонки/неконсистентного lifecycle-снапшота у `generic-shell`.

### Изменение в установленном дистрибутиве (ProjectForge)
- На уровне runtime-driver (в дистрибутиве `processforge`):
  1. Добавить явную детекцию `stop requested` до `process.collect` и логгирование причин/времени в `status/heartbeat`,
  2. При отсутствии `heartbeat` создавать его с явным terminal-сигналом (`cancelled`/`stop_requested`) и причину, чтобы исключить «тихие» застревания между `process started` и `collect`,
  3. Предпочтительно, для write-задач включить прямой `codex-exec` как первичный путь, оставив `generic-shell` как fallback только для диагностических/legacy сценариев.
