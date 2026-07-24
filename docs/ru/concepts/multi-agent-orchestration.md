# Multi-Agent Orchestration

Multi-agent orchestration - это встроенный ProcessForge процесс для разбиения run на ограниченные worker assignments.

Orchestrator создаёт `orchestrator-task-plan.yaml`, проверяет scope rules, применяет plan и затем собирает worker outputs для integration.

Worker получает только:

- свой assignment file
- свою assignment capsule
- разрешённые read/write scopes
- forbidden files
- required outputs
- expected report path

Worker не получает полный project context по умолчанию. Assignment capsule содержит `worker_may_rebuild_context: false`.

## Scope Rules

- Parallel workers не должны иметь пересекающиеся write scopes, если overlap явно не разрешён plan.
- `forbidden_files` имеют приоритет над `allowed_files`.
- Required outputs должны находиться в allowed files worker или в project artifact area.
- Core files можно менять только при явном разрешении.
- Worker останавливается и сообщает, если выданного scope недостаточно.

## Apply Output

`orchestrator-plan apply --apply` создаёт:

- run
- worker task assignments
- assignment capsules
- worker launch prompts
- task index
- orchestration summary
- initial orchestrator handoff
