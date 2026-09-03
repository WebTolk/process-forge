# Отчёт: correct-worker-run-shell-smoke

## corrections
- В `smoke_environment_isolation` восстановлена ожидаемая последовательность проверки: `start -> collect -> проверка отчёта из capsules -> принудительная проверка stale-капсулы` (с учётом фактического статуса `collect` для `running`-задачи).
- Для проверки stale-сценария добавлена принудительная инвалидация `assignment` капсулы (`.pf/assignments/env-isolation.yaml`) до вызова `worker-run prepare`, чтобы подтвердить выдачу `assignment capsule is stale`.
- `ensure_stopped` теперь принимает реальные терминальные статусы (`completed`, `timed_out`, `unknown_exit`, `lost`, помимо `stopped/failed/cancelled`).
- `driver_yaml_path` теперь поддерживает внешний каталог драйвера (`base_dir`) и `smoke_direct_path_recovery` использует временный каталог вне каталога проекта, что проверяет внешний direct-path ad-hoc driver.
- Убраны нестабильные/избыточные ограничения области записи в задаче (`create_task` теперь выдаёт artefact-scoped allowed-file), чтобы не возникали конфликтующие overlaps между заданиями.
- Временные рабочие/driver-деревья создаются через `make_temporary_root` в `ROOT`, очищаются через `shutil.rmtree(..., ignore_errors=True)` в `finally`.
- `smoke_duplicate_start_parallel` перестроен на более устойчивую проверку дедупликации: ожидаем `SKIPPED` исход и отсутствие дублирующих marker-файлов.

## focused_smoke_result
- Команда: `python tools/smoke_worker_run_shell.py`
- Результат: `PASS`

## cleanup_evidence
- После прогона все временные каталоги `.pf-worker-shell-*` удалены, в workspace осталось только рабочее состояние исходного репозитория.
- Для каждого тестового задания выполнялся `stop_if_running` + `ensure_stopped` в финальном `finally`, затем удаление временных директорий.
- Доказательства в ходе запуска: финальный вывод `PASS: worker-run shell regressions smoke` без исключений.