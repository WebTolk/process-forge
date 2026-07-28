# Быстрый старт multi-agent orchestration

Используйте этот сценарий внутри уже подключённого проекта. Его можно понимать
как режим кузницы или фабрики: несколько агентов получают изолированные задачи,
а основной процесс собирает их результаты обратно.

```bash
python .pf/runtime/bin/pf.py orchestrator-plan create --project-root . --run example-run --title "Example multi-agent run" --apply
python .pf/runtime/bin/pf.py orchestrator-plan validate --project-root . --plan .pf/runs/example-run/orchestrator-plan.yaml
python .pf/runtime/bin/pf.py orchestrator-plan apply --project-root . --plan .pf/runs/example-run/orchestrator-plan.yaml --apply
python .pf/runtime/bin/pf.py orchestrator-plan status --project-root . --run example-run
python .pf/runtime/bin/pf.py worker-launch-prompt create --project-root . --task docs-worker --apply
```

Также доступны flat aliases:

- `orchestrator-plan-create`
- `orchestrator-plan-validate`
- `orchestrator-plan-apply`
- `orchestrator-plan-status`
- `worker-launch-prompt-create`

Шаблон plan находится в `templates/orchestrator-task-plan.yaml`.

Чтобы переиспользовать example plan из дистрибутива, запускайте команду из
корня дистрибутива ProcessForge и указывайте подключенный проект через
`--project-root`:

```bash
python bin/pf.py orchestrator-plan create --project-root <project-root> --run example-run --title "Example multi-agent run" --answers examples/multi-agent-orchestration/minimal/orchestrator-task-plan.yaml --apply
```
