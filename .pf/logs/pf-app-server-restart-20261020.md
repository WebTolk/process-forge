# PF App Server restart

## 2026-10-20T08:35:42.942648+00:00 - primary operator action

Task: По прямому поручению пользователя перезапустить App Server; пользователь затем сам перезапустит сессию.
Files changed: Только этот журнал, переносимый отчёт и checkpoint; продуктовый код не менялся.
Artifacts changed: .pf/artifacts/pf-app-server-restart-20261020/report.json; .pf/handoffs/pf-app-server-restart-20261020.md.
Templates used: Established operator log/handoff format.
Tools used: Existing installed PF CLI server status/restart, read-only process identity check, isolated-index Git delivery.
Decisions: Source CLI context fresh/ready; old connected MCP reported stale, unrelated legacy/future current Work was not selected or executed. No context refresh, Core reinstall or terminal Work reuse. Explicit restart is an operator infrastructure action, not continuation of the completed code cycle.
Status: Normal restart refused HTTP409 runtime_busy_or_activity_unknown because activity coverage is partial. Lease metrics showed held=0 with complete coverage; own workers were already stopped/checked out. The requested restart used the canonical --force busy-guard override; partial global activity remains unknown. Restart succeeded, old process ended, different live owner uses the installed entrypoint. health/readiness ready, configuration valid, interval10 retained.
Risks: Actual connected MCP acceptance remains for the user's new session. Installed manifest source remains d6eb1412fb47ad21df50e4c446d0cc813589034e. No other service/session restart, source repair, autostart change or further refactor performed.
Next steps: User reconnects session; first verify real connected pf.context/provenance and exact new task. Do not repeat Core apply or resume completed Work.
Handoff: .pf/handoffs/pf-app-server-restart-20261020.md.
