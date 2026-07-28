# Runtime driver and execution inspector quickstart

Используйте после `workplace-init` и `project-onboard`.

`supervisor` - историческое техническое имя команды. В семантике ProcessForge
этот цикл является Process Execution Inspector: он проверяет assigned task
runtime state и не управляет agent attendance, не выдает leases, не
маршрутизирует процессы и не финализирует handoffs.

Проверьте встроенные нейтральные driver-ы:

```bash
python .pf/runtime/bin/pf.py runtime-driver list --project-root .
python .pf/runtime/bin/pf.py runtime-driver validate --project-root . --driver manual
python .pf/runtime/bin/pf.py runtime-driver validate --project-root . --driver test-echo-worker
python .pf/runtime/bin/pf.py runtime-driver validate --project-root . --driver test-shell-agent
```

Подготовьте ручной worker-run:

```bash
python .pf/runtime/bin/pf.py worker-run prepare --project-root . --task docs-worker --driver manual
python .pf/runtime/bin/pf.py worker-run status --project-root . --task docs-worker
```

Запустите supervised test plan из примера:

```bash
python .pf/runtime/bin/pf.py orchestrator-plan create --project-root . --run supervised-run --title "Supervised run" --answers examples/runtime-supervisor/minimal/orchestrator-task-plan.yaml --apply
python .pf/runtime/bin/pf.py orchestrator-plan apply --project-root . --run supervised-run --apply
python .pf/runtime/bin/pf.py supervisor run --project-root . --run supervised-run --max-ticks 5 --interval 0
python .pf/runtime/bin/pf.py execution-inspector-run --project-root . --run supervised-run --max-ticks 5 --interval 0
python .pf/runtime/bin/pf.py run-status --project-root . --run supervised-run
```

`test-echo-worker` и `test-shell-agent` предназначены для smoke tests и
демонстраций. Реальный запуск worker-а остаётся явным opt-in через runtime
driver manifest. Execution-inspector ticks запускают shell workers detached, на
следующих tick-ах наблюдают process state и собирают required reports только
после успешного завершения worker-а.

Shell-launched proof worker создаёт `status.json`, `command.json`,
`process.json`, `stdout.log`, `stderr.log`, `heartbeat.json`, `exit.json` и
настроенный report artifact. `heartbeat.json` лежит в
`.pf/runtime/agent-runs/<run-id>/<task-id>/heartbeat.json` и содержит минимум
`schema_version`, `run_id`, `task_id`, `status`, `pid`, `timestamp`,
`sequence`. Это отдельный файл: heartbeat показывает текущий process proof, а
`exit.json` фиксирует финальный результат.
