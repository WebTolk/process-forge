# Shell Agent Subagent Policy

Shell agents - это OS processes, запущенные через ProcessForge runtime drivers и bounded supervisor.

Каждый worker получает только свою assignment, assignment capsule, разрешенный write scope, read scope, forbidden scope, required outputs и `subagent_policy`. Shell worker может вызывать subagents только если capsule policy это разрешает.

Поля shell-agent config задают поведение, а не являются рекомендациями. `allow_subagents` и `subagent_policy` копируются в generated assignment capsule. `worker-run collect` проверяет required worker outputs, expected report artifact и subagent reports только когда `subagent_policy.allow=true` и `subagent_policy.require_reports=true`.

Если отчеты обязательны, shell worker пишет их в `.pf/artifacts/subagents/<worker-id>/`. Workers с `allow_subagents=false` не обязаны создавать subagent reports. Public smoke использует нейтральные simulated reports и не зависит от Claude, Codex, Gemini, Cursor или OpenCode CLI.

`orchestrator-shell-plan-apply` пишет `.pf/runs/<run-id>/config-resolution-report.yaml`, чтобы оператор видел, какие значения config применены к assignments, capsules, supervisor scheduling и collection checks.
