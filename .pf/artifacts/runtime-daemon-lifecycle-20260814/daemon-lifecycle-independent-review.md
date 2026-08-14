PASS: Критичных расхождений с целевым поведением не найдено; архитектурная цель (runtime lifecycle, опирающийся на `instance_id`) в целом подтверждена. Обнаружено 1 замечание с уровнем WARN для edge-case восстановления.

## PASS (подтверждение требования `instance-id`)

- Серьезность: PASS
- Файл/функция/строка: `tools/pf_runtime/service.py:152-179` (`inspect_lifecycle`), `243-238` (`acquire_singleton`), `594-603` (`status_payload`), `651-679` (`runtime_request` + маршруты команд через host)
- Воспроизведение:
  1) В `runtime.start` инициируется проверка `inspect_lifecycle()`, где жизненный цикл daemon-экземпляра вычисляется через `runtime.lock` и `service.json` с `instance_id`.
  2) В `acquire_singleton` используется `instance_id` как привязка владеющего процесса.
  3) Для операций состояния/запросов runtime используется delegation в host/сердечник PF (`host.tick_payload`, `host.ingest_event`, `host.project_state_payload`, `host.resolve_payload`), то есть runtime хранит только процессный lifecycle и IPC, а не дублирует ядро PF.
- Воздействие: соответствует задаче — runtime не реализует дублирующий lifecycle PF Core, а работает как thin runtime-слой с авторитетным `instance_id`.
- Прямые доказательства:
  - `inspect_lifecycle()` берёт identity из `lock`+`service.json` (`instance_id`, `pid`, `endpoint`).
  - `acquire_singleton()`/`release_singleton()` управляют владением только через `runtime.lock` + `instance_id`.
  - `status_payload()` и `runtime_request()` обращаются в host/ядро для project/work-state операций.

## WARN-1: Риск двойного запуска при потере `runtime.lock` при живом старом процессе

- Серьезность: WARN
- Файл/функция/строка: `tools/pf_runtime/service.py:152-167` (`inspect_lifecycle`), `194-199` (`cleanup_stale_runtime`), `489-507` (`command_start`), `547-580` (`command_stop`)
- Воспроизведение:
  1) Запустить `runtime start` (получить живой daemon).
  2) Оставить `service.json` (со старым PID/running), но удалить `runtime.lock` (или сделать его недоступным).
  3) Запустить `runtime start` повторно.
  4) Проверить, что новый процесс стартует, хотя старый может продолжать жить.
  5) Вызвать `runtime stop`: для состояния `stale` остановка идёт по ветке “not running”/без жёсткого завершения старого PID.
- Воздействие: возможна конкуренция двух daemon-процессов с разными моментами состояния в пределах одного workplace, неконсистентность `service.json` и утрата детерминизма IPC/логов.
- Прямые доказательства:
  - В `inspect_lifecycle()` отсутствие lock приводит к нелокальной классификации в `stale`.
  - `command_start()` для `stale` запускает новый процесс после `cleanup_stale_runtime`, без проверки `process_pid_running(state["pid"])` при потере lock.
  - `command_stop()` жёстко завершает PID только для состояний `starting`/`stopping`/`failed`; для `stale` не выполняет terminate, а сообщает “not running” после очистки/пометки состояния.
