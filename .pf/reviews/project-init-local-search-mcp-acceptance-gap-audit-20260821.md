# Acceptance gap audit

Статус: `not_ready_for_final_acceptance`.

Аудит выполнен по выданной capsule и только по разрешённым read-sources. Новые live-тесты/doctor/release-gates не запускались; учитывались только код и уже сохранённые durable artifacts.

## Подтверждённое покрытие

- Есть общий Core service для init/status/repair: `src/processforge_core/project_initialization.py:33-68`, `105-147`.
- CLI `project-onboard`/`init-project` вызывает `project_initialization.initialize_project`, а `project-init-repair` вызывает `repair_project`: `tools/processforge.py:5836-5857`, `5860-5874`.
- MCP facade содержит `pf.project_initialization.*`, `pf.search`, `pf.session_context` и Ledger/session checks: `tools/pf_runtime/mcp_server.py:16-28`, `49-80`, `100-121`.
- `pf.search` требует fresh/fresh_with_updates snapshot перед поиском: `tools/pf_runtime/mcp_server.py:103-107`.
- Search core не делает workplace/global traversal сам по себе; corpus строится из snapshot records: `src/processforge_core/local_resource_search.py:74-114`.
- `pf.session_context` возвращает process/stage obligation projection из PF facts: `tools/pf_runtime/session_read.py:107-174`.

## Acceptance gaps

### 1. BLOCKER: отсутствуют финальные proof/review artifacts из master prompt

В durable folder есть implementation/remediation/design reports, но нет точных expected artifacts:

- `project-initialization-implementation-report.md`
- `mcp-search-implementation-report.md`
- `project-initialization-proof.md`
- `mcp-search-proof.md`
- `independent-architecture-review.md`
- `independent-code-review.md`
- `final-validation.md`

Это напрямую блокирует DoD items `24-26`: release/archive gates, independent reviews, `git diff --check` final proof. Текущие отчёты содержат локальные PASS-заявления для `py_compile`, smoke и `git diff --check`, но нет единого final validation artifact.

### 2. HIGH: template search не доказан и, вероятно, не покрыт producer-ом

Snapshot producer формирует `local_search_resources` только из `available_knowledge_resources`: `tools/processforge.py:9777-9791`. При этом `resolved.templates` содержит только `{id, status}` без root/path metadata: `tools/processforge.py:9901-9903`.

Smoke проверяет knowledge-like allowed directory and outside token, но не fixture с template package и запросом вроде `Joomla plugin manifest`: `tools/smoke_project_init_local_search_mcp.py:27-34`, `64-89`.

Acceptance tests `33. Template search` и DoD `13. Template search PASS` не закрыты доказательством.

### 3. HIGH: `pf.search` не возвращает локальный путь к файлу в смысле master prompt

Master prompt требует главный результат как локальный путь, чтобы агент читал файл обычными средствами Codex. Текущий result отдаёт `canonical_path` относительно authorized root и synthetic `path_ref`, но не physical local path: `src/processforge_core/local_resource_search.py:205`.

MCP runtime специально раскрывает physical root только в request-local copy и “never persisted or returned”: `tools/pf_runtime/mcp_server.py:113-117`.

Это может быть правильной privacy-границей, но тогда нужен подтверждённый follow-up resolve/read contract. В текущих разрешённых файлах такого proof нет. Acceptance tests `13`, `15`, DoD `11` закрыты неполно.

### 4. HIGH: init contract не имеет явных specialization/platform/process inputs на CLI/MCP surface

Core request normalization принимает `project_root`, `workplace`, `answers`, `project_type`, `coordination_mode`: `src/processforge_core/project_initialization.py:79-102`.

MCP initialize schema также публикует только `answers`, `project_type`, `coordination_mode`, `force`, `allow_missing_workplace`: `tools/pf_runtime/mcp_server.py:133-134`.

CLI `project-onboard` требует `--type`, но не имеет явных `--specialization`, `--platform`, `--process`: `tools/processforge.py:24573-24583`.

Если specialization/platform/process могут передаваться через `answers`, это нужно зафиксировать и доказать acceptance fixture. Сейчас acceptance test `30. Complete initialization` именно с specialization/platform/process не подтверждён.

### 5. MEDIUM: partial initialization detection покрыта только фиксированным подмножеством

Status read model проверяет `.pf`, snapshot existence, `context.status`, blocked health и фиксированный список deterministic artifacts: `src/processforge_core/project_initialization.py:20-25`, `42-50`.

Master prompt требует обнаруживать также registry entry без deterministic artifacts, platform задана но knowledge resolution неполный, process задан но обязательный assignment отсутствует, stale snapshot, doctor FAIL. Часть этого может ловиться через `project_context_check_result`/doctor, но в `project_initialization.status` нет явного registry/process-required-assignment/doctor summary proof: `src/processforge_core/project_initialization.py:68`.

### 6. MEDIUM: exact knowledge search scope fixture A+B vs C не доказан

Smoke доказывает, что файл вне authorized root не находится, и что чужой project_root даёт `session_project_mismatch`: `tools/smoke_project_init_local_search_mcp.py:25-34`, `67-84`.

Но master acceptance `32` требует fixture, где snapshot содержит knowledge A+B, workplace также содержит matching knowledge C, и `pf.search` возвращает A, не видя C. В разрешённых proof artifacts такого сценария не найдено.

### 7. MEDIUM: durable Codex tool visibility audit устарел относительно текущего кода

`codex-mcp-tool-visibility-audit.md` утверждает, что текущий facade не имеет `pf.search` и initialization operation. Текущий `mcp_server.py` уже содержит `pf.search` и `pf.project_initialization.*`: `tools/pf_runtime/mcp_server.py:16-28`.

Это не продуктовый regression, но durable artifact больше не отражает финальное состояние. Без `final-validation.md` и refreshed visibility proof DoD `18` остаётся неполным.

### 8. MEDIUM: EN/RU documentation update не доказан полностью

Разрешённые docs показывают English updates для initialization/repair и Runtime MCP: `docs/authoring/project-initialization.md:1-48`, `docs/concepts/runtime-mcp.md:1-21`.

Master требует EN/RU встроенную документацию. В allowed sources не было RU doc artifact/path, подтверждающего parity по `pf.search`, `pf.resolve`, snapshot boundary, local-resource precedence, session_context guidance и MCP fallback. DoD `21` не доказан.

## Итог

Кодовая база уже содержит значимую реализацию shared init/repair, Ledger-bound MCP и snapshot-authorized FTS search. Но финальный acceptance нельзя считать закрытым: отсутствуют обязательные proof/review/final artifacts, template search не покрыт, search result contract не даёт подтверждённый локальный путь для Codex-чтения, explicit specialization/platform/process init fixture не доказан, а часть durable reports устарела относительно текущего кода.