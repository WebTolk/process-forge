# PF Runtime MCP facade

`tools/pf_runtime/mcp_server.py` — минимальный stdio MCP-сервер. Процессом
владеет host: Codex запускает Python-процесс из своей MCP-конфигурации и владеет
stdin/stdout pipes. Этот сервер не регистрируется как Windows scheduled task или
detached background service.

Garage read tools принимают явный `project_root` и не требуют session identity,
hooks, daemon, Ledger event, Director process или chat transcript. Session и
Forge tools по-прежнему требуют session identity (`--session`,
`PF_MCP_SESSION_ID` или `session_id`), которая уже существует в Agent Ledger.

Обычная инициализация проекта не зависит от host и не устанавливает Codex
hooks, а также не запускает Runtime infrastructure. Телеметрия Codex hooks —
опциональная host-интеграция, которую оператор включает явно, если нужен сбор
Forge sessions.

Доступные tools: `pf.context`, `pf.project_state`,
`pf.project_initialization.status`, `pf.project_initialization.initialize`,
`pf.project_initialization.repair`, `pf.work_state`, `pf.work.state`,
`pf.work.start`, `pf.work.transition`,
`pf.resolve`, `pf.search`, `pf.workplace_state`, `pf.session_context`,
`pf.session_chat` и `pf.session_activity`.

`pf.context`, `pf.project_state`, `pf.project_initialization.status`,
`pf.work_state`, `pf.work.state`, `pf.resolve` и `pf.search` являются Garage
read-операциями и могут работать от `project_root`. `pf.work.start` и
`pf.work.transition` являются Garage-scoped governed mutations и также могут
работать от `project_root`. Три `pf.session_*`
tools дают ограниченные Ledger-authorized views и не читают raw provider
payloads.

`pf.resolve` читает metadata выбранного ресурса из resolved context текущего
проекта, а не заставляет агента искать workplace или угадывать приватные пути.
`pf.search` ищет только по fresh snapshot-authorized local corpus и не
переходит к workspace или web scan.

`pf.project_initialization.initialize` и `pf.project_initialization.repair` —
governed maintenance actions. Они используют тот же Core service, что CLI
onboarding/repair, и требуют точное JSON-значение `apply: true`; иначе
возвращается `apply_required`.

`pf.work.start` — предпочтительный переход от Garage-понимания к governed work.
Агент передает только непустой `objective`; ProcessForge проверяет и закрепляет
process definition, выбирает объявленную initial stage, создает или повторно
использует Run и Assignment. Далее агент вызывает `pf.work.state` и
`pf.work.transition(outcome, evidence)`. Следующая stage не является входом
агента. Session id может связать
telemetry, но сам факт session не меняет `mode: garage` на `mode: forge`.

Session-scoped failures возвращают стабильные machine-readable error codes. Для
`missing_session` payload также содержит ограниченный remediation object:
использовать Garage tools, если операция не требует Ledger session, либо
попросить оператора проверить настроенную host-интеграцию перед повторным
вызовом Forge-only tool. Обычный проектный агент не должен устанавливать hooks
или запускать Runtime как способ исправления. Ручной `session-start` остаётся
операторской диагностикой и не должен создавать вымышленные production session
ids.

Для разрешенного результата `pf.search` поле `local_path` является приватным
runtime navigation value. Оно не записывается в public snapshot, capsules,
reports или registries. Значение выдается только после snapshot authorization,
fresh-snapshot validation, path-ref containment и проверки, что файл принадлежит
authorized root результата.

`pf.work_state` сохранён как compatibility alias для `pf.work.state`. Состояние
выводится из канонических Run и Assignment и закреплённого Process definition;
technical projectors остаются declaration-driven.

MCP не является raw-ingress API и не раскрывает workplace raw payloads.
`pf.session_chat` показывает только trusted redacted private transcript для той
же Ledger session. См. [Codex Session Read Layer](../../concepts/codex-session-read.md) и
[Hooks и события](hooks-events.md).

Codex host registration можно проверить, установить или удалить командами
`python bin/pf.py codex-mcp status|install|remove --workplace <workplace>`.
Install и remove по умолчанию dry-run и требуют `--apply` для изменения Codex
configuration. После изменения регистрации перезапустите или reload Codex.
