# Shell Agent Subagent Policy

Shell agents - это OS processes, запущенные через ProcessForge runtime drivers и bounded supervisor.

Каждый worker получает только свою assignment, assignment capsule, разрешённый write scope, read scope, forbidden scope, required outputs и `subagent_policy`. Shell worker может вызывать subagents только если capsule policy это разрешает.

Если отчёты обязательны, shell worker пишет их в `.pf/artifacts/subagents/<worker-id>/`. Public smoke использует нейтральные simulated reports и не зависит от Claude, Codex, Gemini, Cursor или OpenCode CLI.
