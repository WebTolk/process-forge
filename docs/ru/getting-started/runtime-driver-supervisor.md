# Runtime Driver And Supervisor Quickstart

Используйте после `workplace-init` и `project-onboard`.

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
python .pf/runtime/bin/pf.py run-status --project-root . --run supervised-run
```

`test-echo-worker` предназначен для smoke tests и демонстраций. Реальный запуск
worker-а остаётся явным opt-in через runtime driver manifest.
