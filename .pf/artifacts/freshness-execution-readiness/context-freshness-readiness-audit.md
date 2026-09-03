# Context Freshness Readiness Audit

Дата: 2026-08-23

## Scope

Проверены:

- snapshot producer: `build_project_context_snapshot()`;
- freshness calculation: `project_context_check_result()`;
- CLI diagnostics: `project-context-check`, `project-context-refresh`, `search-index refresh`;
- MCP read path: `pf.session_context`, `pf.search`, `pf.resolve`;
- capability resolution: project registries, active resource profile, platform requirements.

## Finding

Release blocker находился в `project_context_check_result()`: missing required
capabilities попадали в `broken_refs`, после чего весь snapshot получал
`status: broken`. Это блокировало read-only MCP поиск через `snapshot_not_fresh`
даже когда Joomla resources были корректно resolved.

## Correct Boundary

- Freshness: соответствие snapshot текущим sources, requirements и resolved resources.
- Resource readiness: валидность resolved resource/platform/specialization слоя.
- Execution readiness: возможность выполнить текущую работу с доступными capabilities.

Missing `filesystem.read` или `filesystem.write` является execution blocker, но
не resource freshness failure.

## Evidence

До исправления реальный Joomla temp project имел:

- Joomla resources in snapshot: 31;
- missing capabilities: `filesystem.read`, `filesystem.write`;
- MCP `pf.search`: `snapshot_not_fresh`.

После исправления:

- `project-context-check`: `status=fresh`;
- `resource_readiness.status=fresh`;
- `execution_readiness.status=blocked`;
- `pf.search("docs.joomla")`: `search_status=fresh`, `total=25`;
- `pf.resolve("docs.joomla-toolkit:root")`: `status=available`.
