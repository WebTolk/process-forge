# Сводный отчёт: Garage/Forge Stabilization

Дата: 2026-08-24
Проект: `D:\Dev\process-forge`

## Что сделано в предыдущем задании

Предыдущее задание из
`задания/process-forge-stabilization-garage-forge-master-prompt.md` было
оформлено run `stabilization-garage-forge-20260824`.

Реализовано:

- `project-onboard` теперь устанавливает проектный `.codex/hooks.json`;
- `project-init-status` показывает блок `codex_integration`;
- `project-init-repair --repair-action install_codex_hooks --apply`
  восстанавливает отсутствующие или stale Codex hooks;
- `doctor-project` проверяет эффективную защиту `.codex/hooks.json` через
  `git check-ignore`;
- добавлены smokes:
  - `tools/smoke_project_init_codex_integration.py`;
  - `tools/smoke_doctor_gitignore_effective_protection.py`;
- обновлены docs:
  - `docs/concepts/project-init.md`;
  - `docs/validation/doctor-project.md`;
- созданы аудитные/приёмочные артефакты по Runtime, Codex integration, search
  readiness, projection consistency, agent instructions, telemetry и reviews.

Проверки предыдущего среза проходили:

- `py_compile` по изменённым Python-файлам;
- `smoke_codex_integration`;
- `smoke_project_init_codex_integration`;
- `smoke_doctor_gitignore_effective_protection`;
- `smoke_project_init_acceptance`;
- targeted `release-test`;
- `doctor-project`;
- `events-validate`;
- `run-doctor`;
- `git diff --check` с CRLF warnings.

Осталось неполным:

- реальный fresh Codex SessionStart в новом хост-сценарии;
- live MCP bootstrap/search readiness в Codex;
- Forge Runtime acceptance в полном daemon/host смысле.

## Что сделано в текущем задании

Текущее задание из
`задания/process-forge-garage-stabilization-after-new-project-test-master-prompt.md`
оформлено run `garage-stabilization-after-new-project-20260824`.

Baseline показал:

- project context fresh: `ctx-20260824-083958-50e142`;
- execution readiness ready;
- project-local Codex hooks installed;
- MCP in project initialization status: `not_configured`;
- search index fresh and FTS5 available, but `RESOURCES: 0` and
  `DOCUMENTS: 0`;
- Runtime status: `stopped`, `health=stopped`,
  `runtime_version=1.0.0-poc`, `processforge_core_version=1.0.2`.

Реализовано:

- MCP `missing_session` теперь возвращает actionable remediation вместо голого
  кода ошибки;
- MCP schema для `pf.project_initialization.repair` теперь включает
  `install_codex_hooks`;
- `update_stale_agent_presence()` синхронизирует stale-статус в
  current-session projections;
- добавлены smokes:
  - `tools/smoke_mcp_missing_session_diagnostics.py`;
  - `tools/smoke_session_projection_expiry.py`;
  - `tools/smoke_fulltext_article_indexing.py`;
- новые smokes зарегистрированы в `release-test`;
- обновлены docs:
  - `docs/concepts/runtime-mcp.md`;
  - `docs/concepts/resource-search-index.md`;
- создан design для будущего governed work bootstrap;
- создан telemetry пакет:
  - `extended-telemetry-report.md`;
  - `extended-telemetry-statistics.json`;
  - `extended-telemetry-timeline.csv`.

Проверки текущего среза:

- `py_compile`: pass;
- новые smokes напрямую: pass;
- предыдущие Garage smokes: pass;
- selected `release-test` по пяти Garage smokes: pass;
- `project-context-check`: fresh/ready;
- `doctor-project`: pass с существующим WARN по self-contained runtime bin;
- `events-validate`: pass;
- `git diff --check`: pass, только CRLF warnings.

## Итоговое состояние

Два задания существенно укрепили Garage path:

- Codex hook installation теперь является частью project onboarding/repair;
- отсутствующие hooks диагностируются и чинятся штатным PF способом;
- MCP failure до session binding стал объяснимым и ремонтопригодным;
- stale Ledger presence больше не оставляет current-session projection
  ошибочно online;
- FTS fulltext доказан на реальной article fixture;
- search readiness теперь разделён на инфраструктурную свежесть и наличие
  индексируемого корпуса.

## Оставшиеся обязательные gates

Полный master DoD не закрыт, потому что часть проверок требует внешнего нового
Codex host/session состояния:

1. открыть свежую Codex session после установки `.codex/hooks.json`;
2. доказать реальный `SessionStart -> raw ingress -> Ledger`;
3. доказать Codex-visible ProcessForge MCP tools без ручного session id;
4. доказать успешный Ledger-bound `pf.search` из реального Codex MCP;
5. решить продуктовую ясность Runtime version labels;
6. реализовать полноценный governed-work bootstrap API;
7. автоматизировать lifecycle stale/historical marking для derived reports.

## Основные файлы результата

- `.pf/artifacts/stabilization-implementation-report.md`;
- `.pf/artifacts/stabilization-implementation-report-after-new-project.md`;
- `.pf/artifacts/final-validation.md`;
- `.pf/artifacts/final-validation-after-new-project.md`;
- `.pf/artifacts/garage-stabilization-combined-report-20260824.md`;
- `.pf/logs/stabilization-garage-forge.md`;
- `.pf/logs/garage-stabilization-after-new-project.md`.

Итог: `pass_with_conditions`.
