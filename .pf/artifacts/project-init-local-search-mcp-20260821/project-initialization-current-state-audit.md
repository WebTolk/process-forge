# Отчет по артефактам MCP-инициализации (исходный источник: `project-initialization-contract.md`)

## project-initialization-current-state-audit

**Источник:** accepted `project-initialization-contract.md` (раздел `project-initialization-current-state-audit`).

Текущий `project-initialization` уже имеет базовый жизненный цикл: `intake`, `workplace-resolution`, `repository-scan`, `project-classification`, `global-resource-matching`, `project-specificity-extraction`, `proposal`, `review`, `apply`, `doctor`. Артефакты включают `mcp-capability-report`, `toolchain-detection-report`, `project-package-draft`, `project-doctor-report`.

CLI поверхность: `init-project`, `project-init` и `project-onboard` делегируют в `command_init_project`; `project-onboard` требует явный `--type`. Apply создаёт `.pf` структуру, публичный/локальный манифесты, отчёты, launcher, first assignment, refresh snapshot и запускает `doctor-project`.

Пробелы текущего состояния:
- `docs/processes/project-initialization.md` фиксирует `error_handling: none`; контракт `status/initialize/repair` отсутствует.
- `mcp-capability-report` заявлен как артефакт, но в process docs нет явного live-gate для `codex mcp list`, `/mcp`, `/hooks` и Ledger-bound `pf.session_*`.
- В snapshot `available_mcp`, `activated_mcp`, `tools`, `templates` пустые; MCP facade есть в коде, но не активирован как ресурс текущего профиля.
- `pf.work_state` читает projection `stage-obligations`; rebuild происходит через `runtime-host tick` или `runtime-host rebuild-projections`, а не при read.
- По разрешённым файлам явного release smoke для stdio MCP handshake/tools-list/tools-call/session mismatch не подтверждено.
- `mcp-register` имеет `--dry-run`/`--apply` в CLI, но видимая функция пишет registry при любом не-`dry_run` вызове; это следует закрыть отдельным apply-контрактом до консольной автоматизации.

## local-resource-search-design

**Источник:** accepted `project-initialization-contract.md` (раздел `local-resource-search-design`).

SQLite FTS5 нужен как производный локальный search cache, не как новый authority.

Источник истины:
- project context snapshot: `resolved.available_knowledge_resources`, `resolved.knowledge_resources`, resource metadata, package ids, fingerprints;
- workplace registries доступны только через snapshot-authorized metadata или private runtime access;
- private path resolution остаётся вне публичных artifacts.

Индексируемые поля:
- `resource_id`, `package_id`, `instance_id`, `kind`, `title/name`, `tags`, `summary`, `resolved_version`, `resolved_generation`, `fingerprint`, `path_ref`;
- content snippets индексируются только если assignment/workspace_access явно выдал resource и политика разрешает read.

Lifecycle:
- build on `project-context-refresh`;
- invalidate on snapshot checksum change, resource fingerprint change, stale marker, package/workplace registry fingerprint drift;
- expose `search_status` with `empty | current | stale | unavailable`;
- FTS query returns metadata refs, not raw private paths.

Текущий инвентарный результат: в разрешённом snapshot нет активных knowledge resources и нет FTS5 источников; значит первый дизайн должен корректно поддерживать пустой индекс.

## codex-mcp-tool-visibility-audit

**Источник:** accepted `project-initialization-contract.md` (раздел `codex-mcp-tool-visibility-audit`).

Существующий MCP facade: `pf.project_state`, `pf.work_state`, `pf.resolve`, `pf.workplace_state`, `pf.session_context`, `pf.session_chat`, `pf.session_activity`.

Граница безопасности:
- stdio MCP read-only;
- требуется Ledger session через `--session`, `PF_MCP_SESSION_ID` или `session_id`;
- configured session mismatch закрывается `session_mismatch`;
- отсутствующая session закрывается `missing_session`;
- project_root в `pf.session_*` является consistency assertion;
- errors наружу возвращают стабильный code без диагностики.

Требуемые gates для Codex visibility:
- `codex mcp list` видит сервер;
- активный клиент `/mcp` видит tools/list;
- `tools/call pf.session_context` с текущей Ledger session успешен;
- неверный `session_id` даёт `session_mismatch`;
- чужой `project_root` даёт fail-closed;
- `/hooks` отдельно подтверждает trusted hook registration.

## workplace-mcp-surface-audit

**Источник:** accepted `project-initialization-contract.md` (раздел `workplace-mcp-surface-audit`).

Workplace MCP модель уже registry-backed: `registries/mcp.yaml` содержит `mcp_servers`; capability providers берутся только из активированных MCP ids; platform/specialization bindings могут требовать или рекомендовать MCP; project overrides могут включать/отключать MCP.

Поверхность должна различать:
- registry configured: запись существует;
- resource activated: выбран platform/specialization/project override;
- snapshot active: MCP попал в current context snapshot;
- Codex visible: host/client реально видит сервер;
- Ledger verified: `pf.session_*` работает на текущей сессии.

Риск: registry registration не равен Codex host visibility. Поэтому `mcp-capability-report` должен показывать оба слоя отдельно.

## workplace-console-design

**Источник:** accepted `project-initialization-contract.md` (раздел `workplace-console-design`).

Консоль допустима только design-only как управляющий слой над registry/process commands.

Основные экраны:
- Project Init Status: state, snapshot health, doctor summary, repair actions.
- Resource Search: snapshot-authorized search, empty-index state, stale-index state.
- MCP Registry: configured/activated/visible/verified matrix.
- Codex Integration: hook status, MCP host status, last verification.
- Repair Plan: ordered dry-run actions с явным apply approval.

Правила консоли:
- default action is dry-run/proposal;
- apply требует явного подтверждения;
- приватные пути не отображаются в public/export views;
- workspace_access показывает ids/path_refs, не raw resolved paths;
- консоль не создаёт platform specialization без явного выбора;
- консоль не пишет product code и не меняет protected artifacts.

## mcp-patterns-for-processforge

**Источник:** accepted `project-initialization-contract.md` (раздел `mcp-patterns-for-processforge`).

Повторно используемые паттерны:
- **Ledger-first authorization**: любой session read начинается с Agent Ledger и project binding.
- **Snapshot-authorized resolution**: `pf.resolve` и search возвращают только metadata из project context snapshot.
- **Read-only MCP facade**: MCP tools не создают bindings, не refresh-ят context и не rebuild-ят projections.
- **Separate visibility layers**: registry configured, context activated, host visible, session verified.
- **Fail-closed errors**: наружу стабильные коды без приватной диагностики.
- **Derived cache only**: FTS5/projections/runtime cache rebuildable; durable authority остаётся в `.pf`.
- **Proposal-before-apply**: registration/repair/console actions сначала пишут или показывают план, затем применяются только по approval.
- **No public private paths**: public artifacts используют ids/path_refs/checksums, а resolved local coordinates остаются в local/runtime слоях.

