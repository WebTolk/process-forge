# harden-worker-run-shell-smoke-report

## corrections

### 1) `smoke_environment_isolation`
- Исправлен запуск на **не-detached** режим:
  - `start_task` теперь принимает параметр `detach`.
  - В `smoke_environment_isolation` используется `detach=False`.
- Добавлен явный regression-драйвер с `inherit_environment=False` (`regression-env-isolation`) для проверки изоляции без протекания `PF_LEAK_TEST_SECRET`.
- После `start` производится `collect` с `expect=0` (успешный collect до stale-check).
- Сохранил проверку `PF_LEAK_TEST_SECRET` в `command.json` и проверку `- leak_keys: \`0\`` в отчёте.
- Оставлен последующий stale-capsule flow с `worker-run prepare` (выполняется после успешного collect).

### 2) `smoke_duplicate_start_parallel`
- Сделан реальный конкурентный запуск двумя `worker-run start` через `threading.Barrier(2)`.
- Оба исхода запуска теперь захватываются и учитываются (две `CommandResult`).
- Добавлены проверки:
  - ровно 2 результата стартов;
  - ровно 1 `RUNNING`;
  - ровно 1 `SKIPPED`.
- Для верификации маркера стартов используется фактический путь `start-pids.log` задачи и ожидается ровно **1** маркер после короткого ожидания стабилизации.

### 3) Небольшие инфраструктурные правки теста
- `driver_yaml_path` расширен:
  - `inherit_environment` (по умолчанию `True`);
  - `task_id_for_marker` для корректной привязки `start-pids.log` к конкретному `task_id`.
- `start_task` расширен параметром `detach` и унифицирован для нужд обоих кейсов.

## focused_smoke_result

Команда:
```bash
python tools/smoke_worker_run_shell.py
```

Результат:
- `PASS: worker-run shell regressions smoke`