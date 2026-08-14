# Review: план исправления `worker-run`

Дата: 2026-08-14
Результат: pass_with_conditions

## Проверенный вход

- `plan-concurrency-start-guard-report.md` — worker завершён, exit contract и
  required report собраны Inspector-ом.
- `plan-driver-provenance-report.md` — worker завершён, exit contract и
  required report собраны Inspector-ом.
- `plan-regression-interface-report.md` — worker завершён, exit contract и
  required report собраны Inspector-ом.

## Принятые выводы

- Дедупликация должна происходить до `prepare_worker_run()` и после observation
  текущего `running` state.
- Для параллельных CLI-вызовов необходим межпроцессный lock; одной проверки
  JSON-состояния недостаточно.
- Provenance direct-path driver-а обязателен для повторного Inspector resolve.
- `--wait` остаётся без изменения; policy-наблюдения не смешиваются с fix.

## Исправления, внесённые orchestrator-ом в итоговый план

1. Не принято предложение запрещать повторный start terminal task: текущий
   `prepare_worker_run()` явно поддерживает новый attempt, поэтому такой запрет
   был бы регрессией совместимости.
2. Не принято добавление `driver_ref` в публично описанный `status.json` и
   schema только ради Inspector. Используется уже private durable `command.json`;
   machine-dependent внешний путь допускается лишь там и только если его явно
   передал пользователь при старте.
3. Не принято утверждение о несуществующих path-validation правилах. План
   опирается на текущий `resolve_runtime_driver()` и требует точной ошибки для
   невалидного сохранённого ref, а не выдуманных ограничений.
4. Исправлено место теста: общий lifecycle должен покрываться в
   `tools/smoke_worker_run_shell.py`, а не в Codex-specific smoke.
5. В scope добавлена защита явного `worker-run prepare`, поскольку он тоже может
   переписать live state до запуска нового процесса.

## Условие перед реализацией

Сначала выполнить шаг provenance, затем lifecycle lock; после каждого шага
запустить соответствующий расширенный generic-shell smoke. Код не изменялся в
этом плановом run.
