# Post-remediation review

## Вердикт

**BLOCKED / acceptance не подтверждён.**

По разрешённым файлам видны корректные remediation-направления: публичные snapshot-пути редактируются, smoke покрывает init/repair/FTS/session obligations, `pf.session_context` теперь возвращает stage identity и stage obligations из projection. Но финальный PASS дать нельзя: assignment требует проверить новые evidence-артефакты и Codex MCP registration, а эти файлы и ключевые runtime/core modules не входят в `allowed_read_files`.

## Scope blocker

Капсула называет обязательными input artifacts:

- `.pf/artifacts/project-init-local-search-mcp-20260821/acceptance-fixtures-proof.md`
- `.pf/artifacts/project-init-local-search-mcp-20260821/codex-mcp-registration-proof.md`
- `.pf/reviews/project-init-local-search-mcp-final-acceptance-review-20260821.md`

Но `allowed_read_files` разрешает читать только:

- `задания/process-forge-project-init-local-search-mcp-master-prompt.md`
- `tools/processforge.py`
- `tools/pf_runtime/session_read.py`
- `tools/smoke_project_init_acceptance.py`

По worker contract я не читал out-of-scope evidence. Поэтому невозможно независимо подтвердить:
- фактический результат acceptance fixture run;
- Codex MCP registration evidence;
- run/task doctor outputs и текущую консистентность `.pf`;
- оставшиеся blockers из финального acceptance review.

## Проверка по доступным файлам

### Public path handling

**PASS по доступному коду.**

- `tools/processforge.py:8281-8284` редактирует absolute resource path в `path_ref: private_resource_paths` и помечает `path_status: private_absolute_path_redacted`.
- `tools/processforge.py:8408-8418` скрывает private parameter source path как `<private-source-ref>`.
- `tools/smoke_project_init_acceptance.py:128-133` проверяет, что snapshot не содержит workplace path и что specialization parameter source имеет `<private-source-ref>`.

### Project init / repair

**PARTIAL PASS.**

- CLI adapter делегирует init/status/repair в единый `project_initialization` service: `tools/processforge.py:5860`, `5873`, `5881`.
- Adapter после init/repair пересобирает snapshot и запускает `doctor-project`: `tools/processforge.py:5794-5815`, `5821-5830`.
- Smoke покрывает полный onboard, partial init, repair deterministic artifact и сохранение semantic user content: `tools/smoke_project_init_acceptance.py:119-152`.

Ограничение: сам `processforge_core.project_initialization` не был в read scope, поэтому внутреннюю идемпотентность и safety repair я подтвердить напрямую не могу.

### Local search fixture coverage

**PARTIAL PASS, есть test gap.**

- Smoke проверяет FTS lifecycle, stale rebuild и `search_unavailable`: `tools/smoke_project_init_acceptance.py:67-95`.
- Snapshot формирует `local_search_resources` только из resolved/available resources и templates: `tools/processforge.py:9803-9839`, `9956`.

Gap: доступный smoke вызывает `processforge_core.local_resource_search.search()` напрямую, а не `pf.search` через MCP. Поэтому по этому файлу не подтверждается Ledger-authorized MCP route `session -> project -> snapshot`, tool description и отсутствие hidden workplace fallback.

### `pf.session_context`

**PASS по доступному коду и fixture.**

- Session authorization идёт через Ledger presence и project_id match: `tools/pf_runtime/session_read.py:46-69`.
- Payload включает active run/task/process/stage и `stage_obligations` с `stage_id`, inputs, outputs, evidence и gates: `tools/pf_runtime/session_read.py:107-165`.
- Smoke проверяет автоматическую смену stage obligations между `architecture-plan` и `implementation`: `tools/smoke_project_init_acceptance.py:156-177`.

### Task/run consistency

**PARTIAL PASS.**

- `run-doctor` вызывает `validate_run_consistency` и эмитит doctor event: `tools/processforge.py:19434-19440`.
- `task-complete` блокирует завершение при отсутствующих required outputs: `tools/processforge.py:19657-19669`.
- `task-doctor` считает verification fingerprint по required outputs / expected report: `tools/processforge.py:19674-19704`.

Ограничение: текущие `.pf` run/task files и doctor outputs не доступны по scope, поэтому фактическую консистентность run `project-init-local-search-mcp-20260821` подтвердить нельзя.

### Codex MCP registration evidence

**BLOCKED.**

В доступных файлах нет достаточного доказательства регистрации/видимости `pf.search` в Codex MCP. `tools/smoke_project_init_acceptance.py:42-63` содержит helper для вызова `pf.session_context` через `mcp_server.py`, но в `main()` он не используется; `pf.search` через MCP fixture не вызывается. Evidence-файл `codex-mcp-registration-proof.md` недоступен.

## Findings

1. **BLOCKER:** required evidence artifacts are outside `allowed_read_files`; acceptance cannot be independently verified.
2. **BLOCKER:** Codex MCP registration for `pf.search` is not verifiable from allowed files.
3. **MAJOR TEST GAP:** accessible acceptance smoke tests `local_resource_search.search()` directly, not the `pf.search` MCP facade.
4. **SCOPE GAP:** actual core implementations for project initialization and local search are outside allowed read scope; only adapters and smoke assertions were reviewed.

## Итог

Кодовые признаки remediation в разрешённых файлах выглядят согласованно с master prompt, особенно по redaction, deterministic repair fixture и `pf.session_context` obligations. Но post-remediation acceptance должен остаться **не принятым** до расширения read scope или предоставления проверяемых evidence snippets в самой capsule.