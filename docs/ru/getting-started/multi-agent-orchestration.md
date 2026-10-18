# Быстрый старт multi-agent orchestration

Этот необязательный сценарий нужен в подключённом проекте, когда выбранный
процесс разрешает делегирование. Обычная работа Garage обходится без него.
Перед apply проверьте входные данные, области чтения и записи, результаты и
зависимости каждого исполнителя. В каждой области должен быть один автор;
неизменяемые капсулы сохраняются.

```bash
python .pf/runtime/bin/pf.py orchestrator-plan create --project-root . --run example-run --title "Example multi-agent run" --apply
python .pf/runtime/bin/pf.py orchestrator-plan validate --project-root . --plan .pf/runs/example-run/orchestrator-plan.yaml
python .pf/runtime/bin/pf.py orchestrator-plan apply --project-root . --plan .pf/runs/example-run/orchestrator-plan.yaml --apply
python .pf/runtime/bin/pf.py orchestrator-plan status --project-root . --run example-run
python .pf/runtime/bin/pf.py worker-launch-prompt create --project-root . --task fixture-worker-a --apply
```

Также доступны flat aliases:

- `orchestrator-plan-create`
- `orchestrator-plan-validate`
- `orchestrator-plan-apply`
- `orchestrator-plan-status`
- `worker-launch-prompt-create`

Создаваемый пример содержит `fixture-worker-a` и `fixture-worker-b`.
Замените демонстрационные задания своими и используйте id из своего плана.
Шаблон `templates/orchestrator-task-plan.yaml` находится в дистрибутиве;
целиком этот каталог в подключённый проект не копируется.

Драйвер по умолчанию `manual` не запускает процесс. Для явного запуска и
проверки результатов см. [драйверы и инспектор](runtime-driver-supervisor.md).

Чтобы переиспользовать example plan из дистрибутива, запускайте команду из
корня дистрибутива ProcessForge и указывайте подключенный проект через
`--project-root`:

```bash
python bin/pf.py orchestrator-plan create --project-root <project-root> --run example-run --title "Example multi-agent run" --answers examples/multi-agent-orchestration/minimal/orchestrator-task-plan.yaml --apply
```
