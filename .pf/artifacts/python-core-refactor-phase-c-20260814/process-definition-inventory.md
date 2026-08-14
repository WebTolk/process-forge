# Inventory: process-definition (Phase C slice)

## 1. Цель резолвера и ключевые символы

- `tools/processforge.py`
  - `ProcessDefinitionRef` описывает контракт результата резолва: `process_id`, `path`, `process`, `origin`, `root`, `catalog_role`, `pack_id`, `active`, `available`, `production_ready`.
    - см. `tools/processforge.py:1054`
  - `official_process_definition_refs(...)` собирает пути официальных process из packs (`packs/official/*/processes/*.yaml`), включает `official`/`available` флаги, `pack_id` и `catalog_role`.
    - см. `tools/processforge.py:12548`
  - `process_root_candidates(...)` определяет корни поиска по порядку (flow project → project root → распределённые root), включая legacy flat-каталоги и `processes/core`.
    - см. `tools/processforge.py:12566`
  - `process_root_yaml_files(...)` и `process_catalog_entries(...)` строят реестр кандидатов, помечая legacy и перезаписывая предупреждения/приоритеты.
    - см. `tools/processforge.py:12579`, `tools/processforge.py:12599`, `tools/processforge.py:12520`
  - `resolve_process_definition(project_root, process_or_path, include_available_official=False, ...)`:
    - при `*.yml/.yaml`: пытается вернуть explicit файл;
    - иначе резолвит по id через `process_catalog_entries(...)`;
    - если найден только неактивный official процесс — выдаёт `SystemExit` с инструкцией `pack-activate`;
    - если не найден — падает `SystemExit`.
    - см. `tools/processforge.py:12693`

## 2. Прямые колл-сайты (`resolve_process_definition`)

- `command_task_create` валидация `--stage` через `resolve_process_definition` (через `process` из `process.id`).
  - `tools/processforge.py:19411`
- `command_runtime_host.project`-цепочки и др. косвенно зависят через `core.resolve_process_definition` в runtime-хосте (см. ниже).
- `command_process_doctor`, `command_process_describe`, `process_definition_path`, `process_definition_exists` — CLI-поверхности, которые на текущем этапе всё ещё через один общий резолвер.
  - `tools/processforge.py:14541`, `tools/processforge.py:14647`, `tools/processforge.py:14167`, `tools/processforge.py:12772`

## 3. CLI reachability

- `tools/processforge.py` маршрутизация CLI уже содержит:
  - `runtime-host` subcommands (init/event/status/project-state/work-state/resolve/tick/rebuild-projections/projection-doctor и др.)
    - `command_runtime_host_*` → `tools/pf_runtime/host.py`
    - см. `tools/processforge.py:25515`
  - `runtime` subcommands через `tools/pf_runtime/service` (`command_runtime_serve`, `command_runtime_start/stop/restart/status/doctor/event/...`)
    - см. `tools/processforge.py:18384`, `tools/processforge.py:25507`
  - Процессные команды, где резолвер используется как shared behavior surface:
    - `process describe/list/doctor`.
    - см. `tools/processforge.py:14639`, `tools/processforge.py:14684`, `tools/processforge.py:14538`

## 4. Runtime host (MCP-like payload chain)

- `tools/pf_runtime/host.py`
  - `resolved_process(...)` — локальный кэш `PROCESS_DEFINITION_CACHE` + вызов `core.resolve_process_definition(...)` с инвалидцией по `mtime_ns`.
    - см. `tools/pf_runtime/host.py:103`
  - `active_execution_records(...)` — для каждого активного задания загружает `process` через `resolved_process` и формирует `stage_id`, `workers`, `stage`-данные для projection/runtime.
    - см. `tools/pf_runtime/host.py:650`
  - `project_state_payload(...)` и `work_state_payload(...)` читают роутинг сессии, контекст, события (`core.event_runtime_paths`) и состояние супервизора.
    - см. `tools/pf_runtime/host.py:643`, `tools/pf_runtime/host.py:687`
  - `resolve_payload(...)` дополняет payload lookup ресурса из `project-context.snapshot` по `resource_id` (knowledge-resource resolution), не делает процесс-специфичный резолв.
    - см. `tools/pf_runtime/host.py:745`
  - `ingest_event(...)` (via `command_runtime_host_event`) пишет событие в durable журнал и добавляет его в runtime event stream (`core.append_process_event`/`ledger_from_event`).
    - см. `tools/pf_runtime/host.py:556`, `tools/pf_runtime/host.py:548`

## 5. MCP и hooks

- `tools/pf_runtime/mcp_server.py`
  - Bootstrap через `src/processforge_core/bootstrap.py`.
  - Tools: `pf.project_state`, `pf.work_state`, `pf.resolve`, `pf.workplace_state`.
  - `tool_result(...)` напрямую делегирует в host payload-функции.
  - см. `tools/pf_runtime/mcp_server.py:8`, `tools/pf_runtime/mcp_server.py:16`, `tools/pf_runtime/mcp_server.py:31`

- `tools/pf_runtime/codex_hooks.py`
  - Нормализация событий от Codex hook (`SessionStart`, `SessionEnd`, `PostToolUse`) → `event` с `project_root`, `session_id`.
  - `dispatch(...)` пытается отправить в long-lived runtime (`service.runtime_request(..., "/event"`) и при неудаче делает fallback в `host.ingest_event(...)`.
  - см. `tools/pf_runtime/codex_hooks.py:47`, `tools/pf_runtime/codex_hooks.py:87`

## 6. Схема и I/O

- Схема процесса: `schemas/process-definition.schema.json` (required fields: `schema_version`, `id`, `name`, `version`, `status`, `description`, `stages`, `roles`, `artifact_definitions`, `gates`, `evolution_policy`, etc.).
  - см. `schemas/process-definition.schema.json` (начало файла).
- Чтение/публикация:
  - чтение YAML процессов: `load_yaml_document/read_yaml_file` из candidates.
  - запись: CLI/host currently writes runtime artifacts/states (host state, project/workplace cache, projection payloadы), но резолвер сам — только чтение + cache-мetadata (path/mtime/process object).

## 7. Текущие смоки, релевантные срезу

- Из `release_test_commands`:
  - `smoke_process_resolver_multiple_roots`
  - `smoke_process_definition_schema_contract`
  - `smoke_runtime_host_poc`, `smoke_long_lived_runtime`
  - `smoke_builtin_process_catalog`, `smoke_builtin_process_pack_completeness`
  - `smoke_process_list_origin_filters`, `smoke_process_id_stable_after_move`, `smoke_process_root_collision_policy`
  - `smoke_pf_project_process_refs_follow_layout`, `smoke_no_removed_process_refs`
  - см. `tools/processforge.py:6540` (секция `release_test_commands`)

## 8. Рекомендованный минимальный shared API set (Phase C)

Рекомендуемый минимальный срез для shared API (без переносов validation/authoring/route/handoff):

1. `tools/processforge.py`:
   - `ProcessDefinitionRef`, `process_root_candidates`, `process_root_yaml_files`, `official_process_definition_refs`, `process_catalog_entries`, `resolve_process_definition`, `process_definition_exists`, `process_catalog_role`
2. `tools/pf_runtime/host.py`:
   - `resolved_process`, `PROCESS_DEFINITION_CACHE`, `project_state_payload`, `work_state_payload`, `resolve_payload`
3. `tools/pf_runtime/mcp_server.py`:
   - tool names + `tool_result(...)` payload mapping
4. `tools/pf_runtime/codex_hooks.py`:
   - `normalized_event(...)`, `dispatch(...)` (event bridge с runtime→host fallback)

Исключено на этом этапе: детальная авторинг-валидация (`command_process_create/apply/authoring_*`), policy routing/doctor-цепочки и route-хендлеры снаружи runtime-пула, кроме того, где они прямо вызывают резолвер.