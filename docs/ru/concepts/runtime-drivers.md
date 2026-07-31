# Runtime drivers

Runtime driver описывает, как ProcessForge может подготовить или запустить
worker task. Это необязательный слой. По умолчанию используется `manual`: он
создаёт материалы запуска и не стартует процесс.

Встроенные нейтральные driver-ы:

- `manual`: подготавливает state и никогда не запускает процесс.
- `generic-shell`: запускает явно указанный executable с аргументами.
- `test-echo-worker`: локальный smoke-test worker, который пишет ожидаемый отчёт.
- `test-shell-agent`: локальный smoke-test shell agent, который пишет report,
  stdout/stderr, process, heartbeat и exit proof artifacts.

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
`{task_id}`, `{agent_run_dir}`, `{driver_id}`, `{capsule_path}`,
`{worker_prompt_path}`, `{expected_report_path}`, `{stdout_path}`,
`{stderr_path}`, `{heartbeat_path}`, `{exit_path}`, `{agent_model}`. Неизвестный placeholder считается ошибкой
валидации.

Если у shell worker задан `agent_model`, ProcessForge передаёт его как
`PF_AGENT_MODEL` и `{agent_model}`. Если driver command не задаёт собственный
`model_args`, при непустой модели автоматически добавляется
`--model {agent_model}`.

Shell-запуск выполняется с `shell=False`, без сетевых разрешений по умолчанию.
ProcessForge не устанавливает agent folders, не создаёт фоновый сервис и не
привязывает registry к конкретной экосистеме.
