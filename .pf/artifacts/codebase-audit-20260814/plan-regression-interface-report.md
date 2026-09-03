# План регрессии интерфейса `worker-run` / CLI-циклов

## test_placement

- **Место для покрытия дефектов:**
  - `tools/smoke_codex_exec_worker.py` — уже содержит scaffold для запусков `worker-run start`, фиктивный драйвер и проверку contract/payload; туда добавляются два регрессионных подкейса в `main()`:
    - `test_duplicate_start_reject` (повторный start одного и того же task).
    - `test_adhoc_driver_path_recovery` (ад-хок путь к драйверу + `execution-inspector-tick`).
- **Дополнительная точка парсера/CLI-циклов (без добавления нового функционала):**
  - `tools/processforge.py` (существующая логика `command_worker_run_start`, `runtime_driver_for_task`, `resolve_runtime_driver`, CLI `worker-run start`), для привязки к поведению:
    - `--wait` объявлен в парсере (`--help` контракт), но в `command_worker_run_start` не используется явно.
    - `execution-inspector-tick` и `worker-run start` уже общими путями идут в `supervisor.tick` и `command_supervisor_tick`.
- **Предлагаемые команды (в стиле smoke-скрипта):**
  1. Дубликат start:
     - `python tools/processforge.py worker-run start --project-root <TEMP_PROJECT> --task regression-dup --driver codex-exec --detach`
     - повторно: `python tools/processforge.py worker-run start --project-root <TEMP_PROJECT> --task regression-dup --driver codex-exec --detach`
     - `python tools/processforge.py worker-run status --project-root <TEMP_PROJECT> --task regression-dup`
  2. Ad-hoc driver + восстановление:
     - `python tools/processforge.py worker-run start --project-root <TEMP_PROJECT> --task regression-adhoc --driver <TEMP>/sleeper.yaml --detach`
     - `python tools/processforge.py execution-inspector-tick --project-root <TEMP_PROJECT> --run <run-id>`
  3. Контроль `--wait`:
     - `python tools/processforge.py worker-run start --project-root <TEMP_PROJECT> --task regression-wait --driver <known-driver> --wait`
     - `python tools/processforge.py worker-run start --project-root <TEMP_PROJECT> --task regression-wait --driver <known-driver>`

## isolation_cleanup

- **Изоляция**:
  - Каждый кейс в отдельном `tempfile.TemporaryDirectory` и отдельном `project-root` / `task id` / `run id`.
  - Для стабильности запусков не использовать общие драйверы/каталоги между кейсами.
  - Перед каждым кейсом: убрать/пересоздать `.pf/runtime/agent-runs/<run>/<task>/` (или целиком `.pf/runtime`), чтобы исключить наследование состояния.
- **Очистка после кейса duplicate start**:
  - прочитать `status.json`; если статус `running`, вызвать `worker-run stop --project-root ... --task regression-dup`.
  - при необходимости убить `pid` из статуса через платформенный API stop/kill.
  - удалить временный проект.
- **Очистка после кейса ad-hoc path**:
  - удалить временный `sleeper.yaml` (путь-драйвер) после проверки.
  - удалить все артефакты задания и `agent-runs` для этого task.
  - убедиться отсутствия остаточных `execution-inspector` результатов/очередей для run.
- **Проверочные инварианты между кейсами**:
  - `status` первого запуска должен соответствовать ожидаемой модели до начала повторных запусков.
  - после завершения кейса — пустые хвостовые состояния (`.pf/runtime/...` и `project-runtime` lock/state) в новом sandbox.

## non_defect_disposition

- `--wait` — **no-change**
  - Поведение сейчас согласуется с объявлением: «ожидать по умолчанию, если не задан `--detach`». Дефекта как такового в текущей логике `worker-run start` не подтверждается; это CLI-долг/инерция документации.
- public-release gate separation (`release-check` vs `release-test --public`) — **test-only policy**
  - В CLI есть механика `public_gate` и отдельный прогон `release-test` с `--public`, но контроль применения на CI/потоке релиза должен быть процессный (pipeline). Нужны регрессионные проверки в пайплайне/догхукинге, но код-логика уже покрывает.
- Исключение `process-forge.local.yaml` из `release_path_is_forbidden` (`private local config`) — **no-change**
  - Исключение уже зашито в `release_path_is_forbidden` и не конфликтует с текущими проверкииями публичной чистоты; поведение объяснимо как policy/intentional exception.