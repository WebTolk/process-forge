## Изменённые тесты
- `tools/smoke_worker_run_shell.py` переработан в регрессионный smoke-скрипт для `worker-run`.
- Добавлен сценарий `smoke_duplicate_start_sequential`:
  - проверка идемпотентного дубля запуска в последовательном режиме (`first RUNNING`, `second SKIPPED`),
  - подтверждение неизменности `pid`,
  - подтверждение отсутствия нового маркера запуска.
- Добавлен сценарий `smoke_duplicate_start_parallel`:
  - одновременный запуск двух `start --detach` через `threading.Barrier`,
  - подтверждение, что остаётся ровно один маркер запуска,
  - подтверждение наличия и `RUNNING`, и `SKIPPED` исходов.
- Добавлен сценарий `smoke_prepare_while_running`:
  - попытка `worker-run prepare` на задаче в состоянии `running`,
  - проверка сохранения `status=running`, неизменного `pid` и неизменной счётности маркеров.
- Добавлен сценарий `smoke_direct_path_recovery_and_legacy_fallback`:
  - direct-path recovery:
    - фиксация `status.driver_id` как неизвестного,
    - установка `command.driver_ref` на прямой путь драйвера,
    - запуск `supervisor tick` и проверка отсутствия ошибки `runtime driver not found`.
  - legacy fallback:
    - установка `command.driver_ref` в отсутствующий путь,
    - сохранение валидного `driver_id` в состоянии,
    - запуск `supervisor tick` и проверка отсутствия падения на `runtime driver not found`.
- Сценарии используются детерминированно из временного runtime, через явные идентификаторы задач и отдельные конфиги драйверов для изоляции.
- Добавлен явный блок очистки:
  - остановка всех задач через `worker-run stop`,
  - проверка перехода в terminal state/не-`running`,
  - завершение через `TemporaryDirectory`.

## tests_run
- `python -m py_compile tools/smoke_worker_run_shell.py` — успешно.

## cleanup_contract
- После выполнения всех сценариев выполняется остановка всех созданных задач в порядке сценариев.
- Для каждой остановленной задачи валидация состояния (не должно оставаться `running`).
- Временный проект создаётся в `tempfile.TemporaryDirectory`, что обеспечивает удаление workspace после завершения теста.
