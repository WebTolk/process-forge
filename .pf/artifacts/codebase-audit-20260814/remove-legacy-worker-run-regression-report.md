# remove-legacy-worker-run-regression

## Что удалено из покрытия
- В `tools/smoke_worker_run_shell.py` удалён регрессионный сценарий **legacy fallback** `state.driver_id` vs `command.driver_ref`:
  - Удалена задача `legacy-fallback`.
  - Удалена часть сценария, где task стартует с валидным `driver_id`, затем принудительно затиралось `command.driver_ref` на отсутствующий путь (`missing/driver/reference.yaml`) и проверялось восстановление к `state.driver_id` через `supervisor tick`.
- Сохранены все остальные целевые проверки:
  - `smoke_direct_path_recovery` (прямой `driver_ref` + восстановление по `driver_id`).
  - `smoke_duplicate_start_sequential`.
  - `smoke_duplicate_start_parallel`.
  - `smoke_prepare_while_running`.
  - `smoke_environment_isolation`.

## Точный удалённый coverage
- Убрана одна регрессия legacy-state/fallback-пути, ранее описанная в функции `smoke_direct_path_recovery_and_legacy_fallback` как `legacy_task` (`legacy-fallback`) и связанный `legacy-fallback-driver`.

## Запуски и результаты
- `python -m py_compile tools/smoke_worker_run_shell.py` — `PASS`.
- `python tools/smoke_worker_run_shell.py` — `FAIL` (ошибка окружения:
  - `PermissionError: [WinError 5] Отказано в доступе` при создании/очистке `temp`-директории, не связана с удалением legacy-сценария, а с правами на `C:\Users\musst\AppData\Local\Temp\pf-worker-shell-*`).