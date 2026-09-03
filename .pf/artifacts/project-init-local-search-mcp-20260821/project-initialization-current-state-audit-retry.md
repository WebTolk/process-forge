# project-initialization-current-state-audit-retry

## Статус

Аудит выполнен в режиме `planning_only` / read-only. Код и артефакты не изменялись. Проверка ограничена только файлами, разрешенными assignment capsule; live doctor/test/MCP запуск не выполнялся, потому что такие команды читают состояние за пределами `allowed_read_files`.

## Проверенные источники

- `.pf/AGENTS.md`
- `.pf/process-forge.yaml`
- `.pf/process-forge.local.yaml`
- `.pf/contexts/project-context.snapshot.yaml`
- `tools/processforge.py`
- `tools/pf_runtime/mcp_server.py`
- `tools/pf_runtime/host.py`
- `tools/pf_runtime/session_read.py`
- `docs/authoring/project-initialization.md`
- `docs/processes/project-initialization.md`
- `docs/concepts/runtime-mcp.md`
- `docs/concepts/codex-session-read.md`
- `packs/official/software-development/processes/software-feature-development.yaml`

## Текущее состояние

- Проектный bootstrap описан как file-first ProcessForge flow: работа идет через assignments, ECP, artifacts, reviews, handoffs, logs; границы задаются assignment scope (`.pf/AGENTS.md:5-18`, `.pf/AGENTS.md:22-34`).
- Manifest проекта включает `processforge-development`, file-only/linked режим, `workplace.reference: auto`, обязательные capability `repository_read`, `markdown_editing`, `schema_validation` и optional `repository_symbol_analysis`, `official_documentation_lookup`, `browser_verification` (`.pf/process-forge.yaml:3-29`).
- Snapshot свежий по дате: `generated_at: 2026-08-21T09:03:53Z`, `valid_until: 2026-08-28T09:03:53Z`; но `snapshot.health.status: blocked` (`.pf/contexts/project-context.snapshot.yaml:1-15`).
- Классификация проекта: `software.python`, platform contracts не выбраны, доступен Joomla contract, но stack пустой (`.pf/contexts/project-context.snapshot.yaml:20-84`).
- В текущем resource profile нет активированных tools, MCP или templates; knowledge packages активированы только из official software/web профиля (`.pf/contexts/project-context.snapshot.yaml:501-566`, `.pf/contexts/project-context.snapshot.yaml:1116-1147`).
- Основной зафиксированный blocker: unsatisfied `research` и `process_governance` для `knowledge-package-improvement`; `review` и `repository_write` удовлетворены active process pack (`.pf/contexts/project-context.snapshot.yaml:573-707`, `.pf/contexts/project-context.snapshot.yaml:875-925`).

## Project Initialization

- CLI поддерживает `init-project`, `project-init` и `project-onboard`; все делегируют в `command_init_project`, при этом `project-onboard` требует явный `--type` (`tools/processforge.py:24486-24523`).
- Apply-flow создает `.pf` директории, пишет проектные файлы, добавляет `.gitignore`, эмитит onboarding events, обновляет project context snapshot, создает launcher, first assignment, запускает `doctor-project` и дописывает doctor status в onboarding report (`tools/processforge.py:5771-5838`).
- Snapshot refresh строит YAML, Markdown, generation snapshot, workplace cache snapshot и refresh report; старые capsules остаются immutable и привязанными к прежнему snapshot id/checksum (`tools/processforge.py:10155-10191`).
- Документация процесса перечисляет стадии от intake до doctor и обязательные артефакты, включая `mcp-capability-report`, `toolchain-detection-report`, `project-package-draft`, `project-doctor-report` (`docs/processes/project-initialization.md:23-55`).
- Authoring doc покрывает dry-run/apply/review, но не описывает live verification для MCP/session read; после apply предлагает ручной review generated reports (`docs/authoring/project-initialization.md:5-34`).

## Snapshot / Doctor

- `project_context_check_result` проверяет наличие snapshot, обязательные schema keys, `valid_until`, stale marker, source fingerprints, classification drift, resource drift, missing required capabilities и возвращает `fresh`, `fresh_with_updates`, `stale` или `broken` (`tools/processforge.py:9512-9634`).
- `doctor-context` проверяет manifest cleanliness, snapshot YAML/MD, freshness, snapshot health, context index/resolved rules/conflict report/cache, `.gitignore`, а при assignment еще ECP freshness/checksums/status (`tools/processforge.py:19872-19959`).
- `doctor-project` проверяет public/private manifest boundary, workplace reachability, distribution checks, hooks, coordination, `.gitignore`, package draft, resource reports, public snapshot path checks и onboarding artifacts (`tools/processforge.py:19962-20189`).
- В текущем snapshot required capabilities доступны, optional capabilities отсутствуют с `warn`; это не blocker само по себе (`.pf/contexts/project-context.snapshot.yaml:1072-1104`).
- Blocked health в snapshot связан не с manifest required capabilities, а с resolved execution route для `knowledge-package-improvement`, где profile не предоставляет `research`/`process_governance`.

## Runtime / MCP

- `mcp_server.py` реализует read-only stdio MCP facade с tools: `pf.project_state`, `pf.work_state`, `pf.resolve`, `pf.workplace_state`, `pf.session_context`, `pf.session_chat`, `pf.session_activity` (`tools/pf_runtime/mcp_server.py:15-23`).
- MCP facade требует session identity: configured `--session`/`PF_MCP_SESSION_ID` или `session_id` argument; mismatch закрывается `session_mismatch`, отсутствие session закрывается `missing_session` (`tools/pf_runtime/mcp_server.py:49-62`).
- Для non-session tools facade сначала проверяет Ledger binding через `host.project_for_session`, затем отклоняет несовпадающий `project_root`; своего второго project binding MCP не создает (`tools/pf_runtime/mcp_server.py:63-78`).
- `session_read.py` авторизует session через Agent Ledger, валидирует project binding, ограничивает лимиты до 100 и возвращает стабильные коды ошибок без диагностики (`tools/pf_runtime/session_read.py:17-69`, `tools/pf_runtime/session_read.py:166-223`).
- `pf.session_context` возвращает project/work/blockers/active_agents/context_freshness/recent_activity; `pf.session_chat` читает transcript через Core; `pf.session_activity` возвращает bounded activity facts (`tools/pf_runtime/session_read.py:107-223`).
- Runtime Host держит только rebuildable cache/session routing, а durable facts остаются в `.pf`; stage obligations строятся из process definitions, assignments, run state и event journal (`tools/pf_runtime/host.py:1-5`, `tools/pf_runtime/host.py:141-303`).
- `pf.work_state` читает generated `stage-obligations` projection, но не пересобирает ее на read; rebuild происходит через event/tick/rebuild-projections (`tools/pf_runtime/host.py:974-1013`, `tools/pf_runtime/host.py:1062-1114`).
- Концепт-доки совпадают с кодом: MCP read-only, Ledger-authorized, не raw ingress, `pf.resolve` берет metadata из project context snapshot, hook/MCP setup opt-in и должен проверяться отдельно (`docs/concepts/runtime-mcp.md:3-22`, `docs/concepts/codex-session-read.md:3-18`, `docs/concepts/codex-session-read.md:36-75`).

## Тестовое покрытие, видимое из разрешенных файлов

- Release suite в `tools/processforge.py` включает общие проверки `py_compile`, schema/public cleanliness, event ingress/replay, conversation completeness, agent ledger, single/multi session flows, runtime host PoC, context snapshot freshness/lock/capsule, capability resolution и `doctor-project` (`tools/processforge.py:6560-6712`).
- В видимом списке release commands есть `smoke_runtime_host_poc`, `smoke_conversation_completeness`, `smoke_agent_ledger`, `smoke_single_agent_session_flow`, `smoke_multi_project_agent_sessions`; явного smoke с именем `mcp_server`, `session_read`, `pf.session_chat` или `pf.session_context` в этом списке не видно (`tools/processforge.py:6594-6602`).
- Само содержимое smoke/test файлов не входило в `allowed_read_files`, поэтому наличие фактического MCP protocol coverage не подтверждено.

## Конкретные пробелы

1. **Snapshot fresh but blocked**: текущий snapshot свежий по TTL, но `health.status: blocked` из-за unsatisfied `research`/`process_governance` для выбранного route `knowledge-package-improvement`. Это нужно закрыть через specialization/platform/process binding или изменить route/scope так, чтобы capability requirements соответствовали доступному profile.
2. **MCP не активирован в текущем context profile**: snapshot показывает пустые `required`, `recommended`, `activated` для MCP. Код и docs MCP facade существуют, но проектный resource profile и assignment workspace access не предоставляют MCP capability.
3. **Project init docs не связывают `mcp-capability-report` с live MCP verification**: process artifacts требуют MCP report, runtime docs говорят проверять `codex mcp list`, `/mcp` и `/hooks`, но в project initialization doc нет явного gate/шаблона для этой проверки.
4. **Нет подтвержденного release-test MCP facade smoke в видимом command registry**: Runtime/session smoke есть, но по разрешенным файлам не найден явный тест stdio MCP handshake/tools-list/tools-call/session mismatch.
5. **Projection freshness зависит от отдельного rebuild/tick/event path**: `pf.work_state` read-only читает `stage-obligations`; если projection отсутствует или stale, read не исправляет состояние. Это ожидаемая архитектура, но должно быть явно учтено в MCP current-state проверках.
6. **Optional repository_symbol_analysis отсутствует в snapshot**: профиль помечает capability как missing/warn; для Python symbol-aware анализа это снижает надежность автоматического audit, хотя не блокирует core flow.

## Рекомендации

- Сначала устранить capability blocker snapshot: выбрать/обновить specialization или process binding, который предоставляет `research` и `process_governance`, либо не использовать `knowledge-package-improvement` route для задач, где эти capabilities не доступны.
- Добавить явный MCP current-state gate в project initialization docs/process artifacts: `codex mcp list`, active client `/mcp`, `/hooks`, проверка `pf.session_context`, `pf.session_chat`, `pf.session_activity` на реальной Ledger session.
- Добавить release/dev smoke для `tools/pf_runtime/mcp_server.py`: initialize, tools/list, missing_session, session_mismatch, invalid project_root, bounded `limit`, `pf.resolve` from snapshot, and no raw payload exposure.
- Для Runtime current-state проверки отдельно запускать `runtime-host rebuild-projections` или `runtime-host tick` перед `pf.work_state`, затем `runtime-host projection-doctor`, чтобы read-only MCP не маскировал stale projection.
- После изменения bindings/docs/tests выполнить minimum gates: `doctor-context`, `doctor-project`, targeted MCP smoke, затем соответствующий process doctor для измененного процесса.