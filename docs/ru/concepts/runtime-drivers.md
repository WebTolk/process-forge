# Runtime Drivers

Runtime driver описывает, как ProcessForge может подготовить или запустить
worker task. Это необязательный слой. По умолчанию используется `manual`: он
создаёт материалы запуска и не стартует процесс.

Встроенные нейтральные driver-ы:

- `manual`: подготавливает state и никогда не запускает процесс.
- `generic-shell`: запускает явно указанный executable с аргументами.
- `test-echo-worker`: локальный smoke-test worker, который пишет ожидаемый отчёт.

Манифесты лежат в `templates/runtime-drivers/`, реестр - в
`templates/registries/runtime-drivers.yaml`. Проект может добавить локальный
реестр в `.pf/runtime/registries/runtime-drivers.local.yaml`.

Команды:

```bash
python .pf/runtime/bin/pf.py runtime-driver list --project-root .
python .pf/runtime/bin/pf.py runtime-driver validate --project-root . --driver manual
python .pf/runtime/bin/pf.py runtime-driver describe --project-root . --driver test-echo-worker
```

Набор placeholders ограничен runtime-фактами: `{project_root}`, `{run_id}`,
`{task_id}`, `{capsule_path}`, `{worker_prompt_path}`,
`{expected_report_path}`, `{stdout_path}`, `{stderr_path}`, `{heartbeat_path}`.
Неизвестный placeholder считается ошибкой валидации.

Shell-запуск выполняется с `shell=False`, без сетевых разрешений по умолчанию.
ProcessForge не устанавливает agent folders, не создаёт фоновый сервис и не
привязывает registry к конкретной экосистеме.
