# Runs, tasks and iterations

![Lifecycle run/task/iteration](../../assets/processforge-run-lifecycle.svg)

Run описывает рабочую сессию. Task — отдельная единица работы внутри run.
Iteration фиксирует повторную попытку или этап работы над task.

Типичный цикл:

```bash
python .pf/runtime/bin/pf.py run-create --project-root . --id <run-id> --title "<title>" --process task-batch-execution --apply
python .pf/runtime/bin/pf.py task-create --project-root . --run <run-id> --id <task-id> --title "<task title>" --process <process-id> --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind work --summary "..." --apply
python .pf/runtime/bin/pf.py task-complete --project-root . --task <task-id> --summary "..." --apply
python .pf/runtime/bin/pf.py run-summary --project-root . --run <run-id> --apply
```

Iterations могут быть `work`, `debug`, `fix`, `review`, `test`, `research`,
`handoff` или `note`.
