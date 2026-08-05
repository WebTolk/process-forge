# Shell agent subagent policy

Shell agents - это OS processes, запущенные через ProcessForge runtime drivers и bounded supervisor.

Эта policy относится к external runtime workers. Она не нужна для стандартного
single-agent session flow, где primary agent владеет execution и использует CLI
checks/gates как inspection. В `single_agent_with_subagents` native subagents
остаются helpers внутри primary session, если они явно не регистрируются и не
делают check-in как отдельные workplace agents.

Каждый worker получает только свою assignment, assignment capsule, разрешенный write scope, read scope, forbidden scope, required outputs и `subagent_policy`. Shell worker может вызывать subagents только если capsule policy это разрешает.

Поля shell-agent config задают поведение, а не являются рекомендациями. `allow_subagents` и `subagent_policy` копируются в generated assignment capsule. `worker-run collect` проверяет required worker outputs, expected report artifact и subagent reports только когда `subagent_policy.allow=true` и `subagent_policy.require_reports=true`.

`orchestrator-shell-plan-apply --model <model>` задаёт модель для всех
shell workers в этом multi-agent plan. Модель записывается в generated
assignments, capsules, worker command state, `PF_AGENT_MODEL` и shell command
model arguments.

Уровень мышления выбирается отдельно. В плане можно задать
`runtime.reasoning_effort`, а конкретный worker может переопределить его через
`reasoning_effort` или `agent_reasoning_effort`. В generated assignments и
capsules итоговое значение хранится как `agent_reasoning_effort`; worker runtime
передаёт его как `PF_AGENT_REASONING_EFFORT`. Драйвер `codex-exec` перекладывает
это значение в `PF_CODEX_REASONING_EFFORT`, а его обёртка добавляет
`model_reasoning_effort="<value>"` для Codex только когда значение не пустое.

Если отчеты обязательны, shell worker пишет их в `.pf/artifacts/subagents/<worker-id>/`. Workers с `allow_subagents=false` не обязаны создавать subagent reports. Public smoke использует нейтральные simulated reports и не зависит от Claude, Codex, Gemini, Cursor или OpenCode CLI.

`orchestrator-shell-plan-apply` пишет `.pf/runs/<run-id>/config-resolution-report.yaml`, чтобы оператор видел, какие значения config применены к assignments, capsules, supervisor scheduling и collection checks.
