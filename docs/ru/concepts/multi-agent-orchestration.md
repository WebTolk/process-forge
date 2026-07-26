# Multi-Agent Orchestration

Multi-agent orchestration - встроенный процесс ProcessForge для разбиения run на ограниченные worker assignments.

Он композирует несколько Primary Agent Sessions. Каждый worker - не sub-persona
внутри orchestrator, а отдельная `1-1-1-1` session со своим `session_id`,
assignment, capsule, scope и output contract. Agent Director / Orchestrator
координирует эти sessions. Стандартный single-agent flow не требует этого
процесса.

Orchestrator создает `orchestrator-task-plan.yaml`, проверяет scope rules, применяет plan и затем собирает worker outputs для integration.

Worker получает только:

- свой assignment file
- свою assignment capsule
- разрешенные read/write scopes
- forbidden files
- required outputs
- expected report path

Worker не получает полный project context по умолчанию. Assignment capsule содержит `worker_may_rebuild_context: false`.

## Scope Rules

- Public config fields задают поведение. Если поле принято в schemas, templates, docs или examples, оно должно влиять на поведение, быть явно описано как metadata-only или падать на validation как unsupported.
- Unsupported public fields падают на validation, если они не помещены в явный `metadata` или `x_` extension namespace.
- Parallel workers не должны иметь пересекающиеся write scopes, если plan явно не задает `allow_write_scope_overlap: true`.
- Когда `allow_write_scope_overlap: true` resolved, generated assignments и capsules записывают allow policy, а supervisor не блокирует workers только из-за пересечения write scopes внутри этого plan.
- `forbidden_files` имеют приоритет над `allowed_files`.
- Required outputs должны находиться в allowed files worker или в project artifact area.
- Core files можно менять только при явном разрешении.
- Worker останавливается и сообщает, если выданного scope недостаточно.

## Apply Output

`orchestrator-plan apply --apply` создает:

- run
- worker task assignments
- assignment capsules
- worker launch prompts
- task index
- orchestration summary
- initial orchestrator handoff
- `config-resolution-report.yaml` со значениями config, примененными к assignments, capsules, supervisor scheduling и output collection
