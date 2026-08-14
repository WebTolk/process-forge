## persistence_contract

- Ключевая причина расхождения: `worker-run` при старте с `--driver <path>.yaml` сохраняет в durable state только `driver_id`, а `execution_inspector` (`supervisor`) в `command_supervisor_tick` повторно разрешает runtime driver только по id (`runtime_driver_for_task(..., state.driver_id ...)`) и не учитывает исходный путь.
- Прямо сейчас этот путь теряется между стартом и Inspector, потому что он не записывается в `schemas/agent-run-state.schema.json`/`status.json`.
- Предлагаемый минимальный контракт:
  - Добавить в durable run-state поле `driver_ref` (new optional, backwards-compatible).
  - `driver_ref` хранит исходную ссылку на driver, если запуск был с ad-hoc ссылкой (обычно путь к файлу).
  - Если запуск через builtin/registry id, `driver_ref` остаётся пустым/не записывается (сохраняем только id).
- Разрешение порядка:
  1) `driver_ref = state.driver_ref`
  2) fallback `state.driver_id`
  3) fallback `worker.runtime_driver` / `task.runtime_driver` / default runtime driver.
- Плюс сохранять в событии/логе `driver_ref` для трассировки после рестарта и при manual recovery.

## compatibility

- Схема остается обратносуместимой:
  - `schemas/agent-run-state.schema.json` уже допускает дополнительные поля (`additionalProperties: true`), значит добавление `driver_ref` не ломает старые readers.
  - Старые `status.json` без `driver_ref` продолжают корректно читать и выполняются по текущему id-пути.
- Не меняется CLI:
  - флаг `worker-run start --driver ...` и существующий формат `runtime_drivers.yaml` остаются прежними.
- Безопасность и валидация:
  - Валидация `driver_ref` при восстановлении/resolve:
    - `suffix` только `.yml/.yaml/.json`.
    - путь должен указывать на существующий файл.
    - файл должен валидно разбираться как YAML/JSON.
    - обязательная валидация полей `schema_version`/`id`/`kind` через существующий `validate_runtime_driver_document`.
    - запрет пустых/некорректных путей (нулевые байты, control chars, path traversal через недопустимые символы), детерминированные ошибки.
  - Предпочтительно нормализовать к абсолютному пути до записи в state (или `project_root`-относительный нормализованный путь), чтобы восстановление после рестарта было детерминированным.
- Изоляция: восстановительный путь не влияет на registry-поиск, пока `driver_ref` валиден; это локальный fallback для только ad-hoc запуска.

## regression_design

- Тест-минимум (детерминированный, сценарный):
  1. Подготовить фикстуру: временный manifest driver `custom/ad-hoc-worker.yaml` с `id: sleeper-ad-hoc` и минимально валидным shell/custom runtime.
  2. Запустить: `worker-run start --project-root <tmp>/proj --task t1 --driver <tmp>/runtime-drivers/custom-ad-hoc.yaml --detach`.
  3. Проверить run-state: `.../.pf/runtime/agent-runs/<run>/<task>/status.json`
     - содержит `"driver_id": "sleeper-ad-hoc"`
     - содержит `"driver_ref": "<resolved path>"` (или эквивалентное нормализованное значение).
  4. Принудительно эмулировать перезапуск инспектора (вызов `execution-inspector-tick --project-root ... --run <run>`), затем убедиться, что ошибка `FAIL: runtime driver not found` больше не возникает и задача переходит в наблюдение/сбор, либо корректный статус для detaching-процесса.
- Проверка совместимости со старым durable state:
  - Создать state без `driver_ref` (или взять существующий fixture), вызвать `inspect`-течение и подтвердить fallback на `driver_id` без regression.
- Безопасность/path-валидация:
  - Негативный тест №1: `--driver not-found.yaml` → понятная failure-сообщение при prepare/start, без падения inspector.
  - Негативный тест №2: файл с невалидным расширением `driver.txt` → reject до запуска.
  - Негативный тест №3: manifest без `schema_version`/`kind` → fail в `validate_runtime_driver_document`, без запуска процесса.
- Метрики детерминизма:
  - Проверка стабильности `status.json` после повторного стартового прохода (только время/статусы меняются по ожиданиям, а `driver_ref` сохраняется неизменно).
