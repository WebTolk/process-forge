# План исправления подтверждённых дефектов `worker-run`

Дата: 2026-08-14
Статус: ready_for_review

## Граница

В реализации остаются только два дефекта, воспроизведённые в изолированном PF-проекте:

1. повторный `worker-run start --detach` способен создать второй процесс для одной
   пары `run_id/task_id`;
2. Inspector не может повторно разрешить driver, переданный явным путём в
   `worker-run start --driver <path>`.

`--wait`, раздельные public release gates и допуск fixture-файлов
`process-forge.local.yaml` не входят в данный change set: это соответственно
CLI debt и policy/CI-вопросы, а не подтверждённые ошибки исполнения.

## Порядок реализации

### 1. Сохранить provenance только для явного path-driver

Файл: `tools/processforge.py`.

1. При `build_worker_process_command()` записывать в уже существующий durable
   `command.json` необязательный `driver_ref` только когда аргумент `--driver`
   был прямым файловым путём. Значение должно быть нормализовано тем же
   `resolve_runtime_driver()` до запуска: project-relative для файла внутри
   проекта, абсолютное только для внешнего явно переданного driver-а.
2. Добавить один helper разрешения driver из durable запуска: сначала
   `command.json.driver_ref`, затем существующий `state.driver_id`, затем
   текущий task/default fallback. Если сохранённый `driver_ref` есть, но больше
   невалиден, вернуть явную диагностическую ошибку; не подменять его driver-ом
   с совпавшим id.
3. Применить helper во всех state-driven путях: `observe_worker_run()` через
   `command_supervisor_tick()`, `command_worker_run_stop()` и failure-path
   `command_worker_run_collect()`.
4. Не добавлять machine path в public артефакты, assignment, event payload или
   `agent-run-state.schema.json`: provenance остаётся в private runtime
   `command.json`, который уже содержит конкретную команду запуска.

Причина порядка: дедупликация должна наблюдать уже запущенный ad-hoc worker тем
же driver-ом, а не вновь разрешать только его id.

### 2. Сделать start/prepare атомарными относительно одной задачи

Файл: `tools/processforge.py`.

1. Ввести короткоживущий межпроцессный lifecycle lock по пути agent-run
   (`run_id/task_id`), который освобождается в `finally`. Он должен охватывать
   проверку durable state, reconciliation, подготовку, `Popen` и запись
   `running`. Простая проверка `status.json` без lock не исправляет гонку двух
   параллельных CLI-процессов.
2. Под lock до `prepare_worker_run()` загрузить существующий state. Для
   `running` разрешить durable driver из шага 1 и вызвать `observe_worker_run()`:
   - если состояние остаётся `running`, напечатать стабильный `SKIPPED`/`already
     running`, эмитировать `worker.run.start_skipped`, вернуть code `0` и не
     изменять `status.json`, `command.json` или PID;
   - если observation перевела запуск в terminal state, сохранить нынешнюю
     семантику нового attempt: подготовить и запустить заново.
3. Применить ту же защиту к `worker-run prepare`: он не должен стирать
   `running` state/exit contract живого worker-а. Для живого запуска — тот же
   no-op с явной диагностикой; terminal state по-прежнему разрешает новый
   attempt.
4. Не менять набор CLI-флагов и не запрещать повторный запуск terminal task:
   это было бы несовместимым изменением текущей семантики `prepare_worker_run()`.
   Новый статус `starting` также не нужен для исправления данной гонки.

## Регрессии

Файл: `tools/smoke_worker_run_shell.py` — это существующий generic-shell smoke,
а не `smoke_codex_exec_worker.py`: дефект лежит в общей lifecycle-логике, и
регрессия не должна зависеть от Codex CLI.

1. Добавить временный direct-path shell-driver с длительностью, достаточной для
   observation (например, Python sleep с durable exit contract).
2. Запустить один `--detach`, затем второй последовательный `start`; проверить
   code `0`, `SKIPPED`, неизменный PID и только один живой дочерний процесс.
3. Запустить два внешних `worker-run start --detach` параллельно для той же
   задачи; проверить тот же инвариант. Этот тест является обязательным для
   межпроцессного lock, а не только последовательной idempotency.
4. Вызвать `worker-run prepare` при живом процессе; убедиться, что PID и
   `running` state не перезаписаны.
5. Запустить тот же direct-path driver, вызвать `execution-inspector-tick` и
   подтвердить отсутствие `runtime driver not found`; проверить сохранённый
   `command.json.driver_ref` и корректный observation/collection.
6. Добавить legacy-совместимость: state/command без `driver_ref` должен
   продолжать разрешаться по `driver_id`. Для несуществующего сохранённого
   `driver_ref` ожидать точную ошибку, а не fallback на иной driver.
7. В каждом кейсе использовать отдельный `TemporaryDirectory`; в `finally`
   остановить живой worker штатной командой и убедиться, что временный проект
   удаляется без orphan process.

## Проверка change set

После реализации выполнить:

```text
python tools/smoke_worker_run_shell.py
python tools/smoke_runtime_driver_registry.py
python tools/validate-process-forge-schemas.py --root .
python tools/processforge.py runtime-driver validate --project-root . --driver codex-exec
python -m py_compile tools/processforge.py
python tools/processforge.py release-test --root . --only smoke_worker_run_shell --no-clean
```

Затем воспроизвести оба сценария в новом temporary PF-проекте, сравнить
`status.json` и `command.json` до/после каждого действия и проверить отсутствие
живых test-PID.

## Откат и критерии готовности

Изменение ограничено `tools/processforge.py` и `tools/smoke_worker_run_shell.py`.
Откат — удалить lifecycle guard/provenance helper и новые smoke-кейсы одним
change set; миграции схем и пользовательских конфигураций не требуются.

Готово, когда оба повторных start (последовательный и параллельный) создают не
более одного процесса, Inspector наблюдает прямой path-driver после старта, а
перечисленные gates проходят.
