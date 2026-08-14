# Implementation Lifecycle Worker Report

## Статус

Выполнено в пределах assignment scope: изменен только `tools/processforge.py`. Smoke-тесты и схемы не редактировались.

## Измененные символы

- `runtime_driver_ref_is_direct_path()` добавлен для отделения прямого file/path driver-ref от registry/builtin driver id.
- `normalized_runtime_driver_ref()` добавлен для сохранения прямого driver-ref как project-relative пути внутри проекта или абсолютного пути только для внешнего явно переданного driver.
- `runtime_driver_for_task()` теперь помечает `_driver_ref` только при явном прямом `--driver <path>`.
- `build_worker_process_command()` теперь сохраняет `driver_ref` в приватный durable `command.json`, когда provenance был явно задан direct-path driver-ом.
- `runtime_driver_for_worker_state()` добавлен для state-driven путей: сначала `command.json.driver_ref`, затем legacy `state.driver_id`, затем task/default fallback.
- `observe_worker_run()` теперь при строковом driver fallback использует durable state resolver, чтобы Inspector/Supervisor не теряли direct-path provenance.
- `worker_run_lifecycle_lock()` добавлен как короткоживущий cross-process lock на пару `run_id/task_id`.
- `worker_run_state_requires_reconciliation()` и `existing_running_worker_run()` добавлены для проверки существующего `running` state под lock без перезаписи живого runtime.
- `emit_worker_run_skip()` добавлен для единообразного `worker.run.start_skipped` / `worker.run.prepare_skipped`.
- `command_worker_run_prepare()` теперь под lifecycle lock делает no-op для живого `running` worker и не стирает `status.json`, `command.json` или PID.
- `command_worker_run_start()` теперь держит lifecycle lock через проверку state, reconciliation, prepare, `Popen` и запись `running`; повторный live start возвращает `SKIPPED` с code `0`.
- `command_worker_run_stop()` и failure-path `command_worker_run_collect()` теперь используют durable state resolver вместо прямого восстановления только по `driver_id`.

## Проверки

- `python -m py_compile tools/processforge.py` — PASS.

## Остаточные риски

- По заданию запускался только `py_compile`; расширенные smoke/release gates не запускались.
- В `tools/processforge.py` уже присутствуют unrelated dirty hunks вне lifecycle/provenance scope; они не нормализовались и не откатывались.
- Lock использует приватный runtime lock-файл и освобождается в `finally`; аварийно оставшийся lock завершит новый lifecycle-вызов диагностикой после таймаута, без stale-lock recovery.