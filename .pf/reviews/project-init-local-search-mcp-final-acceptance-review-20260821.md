# Финальный acceptance review

Статус: **не готово к финальной acceptance**. По разрешённым источникам продуктовая реализация в целом присутствует, но остаются проверенные разрывы именно в acceptance/evidence слое мастер-промпта.

## Проверенные остаточные блокеры

1. **Нет полного proof для clean initialization с `specialization + platform + process`.**  
   `tools/smoke_project_init_local_search_mcp.py` создаёт проекты через `project-onboard --type generic --apply`, а `explicit-bindings-implementation-report.md` подтверждает fixture только с `--process software-feature-development --specialization backend-developer`. В разрешённых доказательствах нет проверки полного набора `specialization/platform/process`, `initialization state = complete` и `doctor PASS` для этого сценария. Блокирует acceptance §30 и DoD 3.

2. **Interrupted initialization / repair acceptance не доказан.**  
   Smoke проверяет `pf.project_initialization.repair` без `apply` и с `apply: true`, но не имитирует частичный сбой после записи части deterministic artifacts, не проверяет отсутствие дублей, сохранение semantic/user content и восстановление missing deterministic state. Блокирует acceptance §31 и DoD 4-5.

3. **FTS5 lifecycle proof неполный.**  
   Текущий smoke доказывает `current`, `stale`, scope-exclusion и `ambiguous_offset`, но не содержит проверок `empty` и `search_unavailable`. Ранее `assurance-audit.md` прямо требовал один запуск, доказывающий `empty/current/stale/unavailable`; это закрыто только частично. Блокирует acceptance gate для search lifecycle.

4. **`pf.session_context` obligations не подтверждены executable proof.**  
   Код `tools/pf_runtime/session_read.py` формирует `work.stage_obligations`, но разрешённый smoke не вызывает `pf.session_context` и не проверяет изменение obligations после смены stage из PF facts. Блокирует acceptance §34 и DoD 15.

5. **Codex behavior / live MCP visibility не доказаны.**  
   Есть raw stdio `tools/list` proof, но нет разрешённого доказательства `codex mcp list`, активного `/mcp`, `/hooks` и реального Codex-first поведения через `pf.search` перед Context7/web/global workplace search. `codex-mcp-tool-visibility-audit.md` сам разделяет эти gates как отдельные live-проверки. Блокирует acceptance §35 и DoD 17-18.

6. **Master-level regression/release/archive gates не подтверждены.**  
   В разрешённых артефактах нет `final-validation.md`, release/archive proof или результата `release-test`/`release-archive-test`; в видимом registry release commands не найден отдельный `smoke_project_init_local_search_mcp` gate. Блокирует DoD 23-24 и 26.

## Итог

Финальную acceptance нельзя закрывать только на текущем evidence set. Минимальный следующий gate: один read/write-capable validation run, который покрывает complete init, interrupted repair, полный FTS lifecycle, `pf.session_context` obligations, Codex/live MCP visibility и release/archive regression proof.