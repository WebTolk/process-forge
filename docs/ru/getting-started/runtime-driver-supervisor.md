# Драйверы исполнителей и инспектор выполнения

Это необязательный сценарий оператора после `workplace-init` и
`project-onboard`, при действительном контексте и разрешённом процессом запуске
исполнителей. Для файловой работы Garage он не нужен. Используйте окружение
из [инструкции установки](installation.md). `execution-inspector-run` —
смысловой псевдоним ограниченного `supervisor run` ниже; выбирайте одну команду.

`supervisor` — историческое техническое имя инспектора выполнения. Он
проверяет состояние назначенных задач и требуемые результаты. Учётом
присутствия агентов, арендой, маршрутизацией и передачей работы управляют
другие компоненты.

Посмотрите и проверьте встроенные нейтральные драйверы:

```bash
python .pf/runtime/bin/pf.py runtime-driver list --project-root .
python .pf/runtime/bin/pf.py runtime-driver validate --project-root . --driver manual
python .pf/runtime/bin/pf.py runtime-driver validate --project-root . --driver test-echo-worker
python .pf/runtime/bin/pf.py runtime-driver validate --project-root . --driver test-shell-agent
```

Для уже существующего назначения можно подготовить ручной запуск.
Вместо `<task-id>` укажите точный id задачи своего плана:

```bash
python .pf/runtime/bin/pf.py worker-run prepare --project-root . --task <task-id> --driver manual
python .pf/runtime/bin/pf.py worker-run status --project-root . --task <task-id>
```

Это отдельная демонстрация тестовых драйверов. Из корня дистрибутива
создайте план, указав фактический путь подключённого проекта:

```bash
python bin/pf.py orchestrator-plan create --project-root <project-root> --run supervised-run --title "Supervised run" --answers examples/runtime-supervisor/minimal/orchestrator-task-plan.yaml --apply
```

Затем из корня подключённого проекта:

```bash
python .pf/runtime/bin/pf.py orchestrator-plan apply --project-root . --run supervised-run --apply
python .pf/runtime/bin/pf.py supervisor run --project-root . --run supervised-run --max-ticks 5 --interval 0
python .pf/runtime/bin/pf.py run-status --project-root . --run supervised-run
```

`test-echo-worker` и `test-shell-agent` предназначены для проверок и
демонстраций. Реальные исполнители запускаются только явно через манифест
драйвера. Инспектор запускает отдельный процесс, наблюдает его на следующих
тактах и собирает обязательные отчёты после успешного завершения.

`supervisor run` выполняет ограниченное число тактов, затем ограниченный
сбор уже запущенных исполнителей без запуска новых задач. `exit.json`
фиксирует окончательный результат, `heartbeat.json` — ход работы,
`status.json` — состояние, наблюдаемое инспектором. Сам отчёт не доказывает
`exit_code=0`.

Shell-launched proof worker создаёт `status.json`, `command.json`,
`process.json`, `stdout.log`, `stderr.log`, `heartbeat.json`, `exit.json` и
настроенный report artifact. `heartbeat.json` лежит в
`.pf/runtime/agent-runs/<run-id>/<task-id>/heartbeat.json` и содержит минимум
`schema_version`, `run_id`, `task_id`, `status`, `pid`, `timestamp`,
`sequence`. Это отдельный файл: heartbeat показывает текущий process proof, а
`exit.json` фиксирует финальный результат.
