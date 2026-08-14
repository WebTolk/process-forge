# Дизайн первого извлечения Catalog API

## Решение по границе
Первый срез должен быть **только catalog/resolve API**. Инвентарь из Phase C рекомендует слишком широкий перенос. В этот срез **не входят**:
- `tools/pf_runtime/host.py::PROCESS_DEFINITION_CACHE`, `resolved_process`, `project_state_payload`, `work_state_payload`, `resolve_payload`, `ingest_event`
- MCP tool mapping и hooks fallback-цепочки
- validation, doctor business logic, authoring, route/handoff checks, runtime transport, worker lifecycle

Причина простая: единственный реально общий и уже используемый CLI + runtime-host seam сейчас это резолв process definition. Всё остальное либо adapter/wiring, либо отдельные предметные срезы с более высоким риском циклов.

## Точный первый срез
Создать только эти новые package-файлы:

```text
src/processforge_core/
  common/
    __init__.py
    ids.py
    paths.py
    yaml_io.py
  process_catalog/
    __init__.py
    models.py
    service.py
```

### Публичные модели
`src/processforge_core/process_catalog/models.py`
- `ProcessDefinitionRef`
- `ProcessCatalogContext`

Рекомендуемый состав `ProcessCatalogContext`:
- `project_root: Path`
- `flow_root: Path`
- `distribution_root: Path`
- `active_official_pack_ids: frozenset[str]`

Это намеренно маленький context. Он уже содержит всё, что нужно catalog API, и не заставляет canonical Core знать про `workplace.yaml`, registries, runtime state или monolith helpers.

### Публичные функции
`src/processforge_core/process_catalog/service.py`
- `process_catalog_role(process: dict[str, Any]) -> str`
- `process_catalog_entries(context: ProcessCatalogContext, *, strict: bool = False, include_available_official: bool = False) -> list[ProcessDefinitionRef]`
- `resolve_process_definition(context: ProcessCatalogContext, process_or_path: str, *, include_available_official: bool = False) -> ProcessDefinitionRef`
- `process_definition_exists(context: ProcessCatalogContext, process_id: str) -> bool`
- `require_official_process_active(context: ProcessCatalogContext, process_id: str) -> None`

Внутренние, неканонические helpers в том же модуле:
- `_official_process_definition_refs(...)`
- `_process_root_candidates(...)`
- `_process_root_yaml_files(...)`
- `_process_override_declared(...)`
- `_official_pack_manifest_records(...)`

## Что именно переносится из `tools/processforge.py`
Переносится только каталог и резолв:
- `ProcessDefinitionRef`
- `process_catalog_role`
- `official_process_definition_refs` по смыслу, но как private helper
- `process_root_candidates` по смыслу, но как private helper
- `process_root_yaml_files` по смыслу, но как private helper
- `process_catalog_entries`
- `resolve_process_definition`
- `process_definition_exists`
- `require_official_process_active`

Не переносится в этот срез:
- `validate_process_definition_files`
- `validate_process_contract`
- `command_process_doctor` business logic
- `normalize_process_authoring_answers`
- `process_from_authoring_answers`
- `build_process_create_plan`
- route/handoff logic
- всё runtime event/work-state

## Legacy wrappers
В `tools/processforge.py` оставить thin wrappers с текущими именами и сигнатурами:
- `ProcessDefinitionRef` как alias на core-модель
- `process_catalog_role(...)`
- `official_process_definition_refs(...)`
- `process_root_candidates(...)`
- `process_root_yaml_files(...)`
- `process_catalog_entries(...)`
- `resolve_process_definition(...)`
- `process_definition_exists(...)`
- `require_official_process_active(...)`
- `process_definition_path(...)`

Задача wrappers только одна: собрать `ProcessCatalogContext` из legacy окружения и вызвать core API. Новую предметную логику в них добавлять нельзя.

## DI и callback boundary
Чтобы canonical Core не импортировал монолит, boundary должен быть таким:

Adapter собирает `ProcessCatalogContext` снаружи core:
- `flow_root` через существующий `locate_flow_root(...)`
- `distribution_root` через существующий `ROOT`
- `active_official_pack_ids` через существующие `resolve_project_workplace_manifest(...)` + `active_process_pack_ids(...)`

Canonical Core:
- не вызывает `locate_flow_root`
- не вызывает `resolve_project_workplace_manifest`
- не читает workplace registries сам
- не импортирует `tools.processforge`
- не зависит от `src/processforge_core/bootstrap.py`

Это минимальная нужная инъекция. Передавать в core `Any core` или набор callback-функций не нужно.

## Runtime host switch
В `tools/pf_runtime/host.py` менять только seam резолва:
- `resolved_process(...)` перестаёт звать `core.resolve_process_definition(...)`
- `resolved_process(...)` начинает строить `ProcessCatalogContext` и звать `processforge_core.process_catalog.resolve_process_definition(...)`

Остальное в `host.py` не переносится и не переписывается:
- `PROCESS_DEFINITION_CACHE` остаётся на месте
- `active_execution_records(...)` остаётся на месте
- `declared_stage_obligations(...)` остаётся на месте
- payload/event/session logic не трогаются

Так runtime host и CLI начинают использовать один и тот же catalog API, но runtime-host остаётся adapter-слоем.

## Обязательные минимальные helpers
Да, первый срез **должен** включать несколько helpers, но только инфраструктурных:
- `src/processforge_core/common/ids.py`: `safe_id`
- `src/processforge_core/common/yaml_io.py`: `load_yaml_document`, `yaml_error`, `read_yaml_file`
- `src/processforge_core/common/paths.py`: `rel`

Почему они нужны:
- без `safe_id` catalog API не сможет сохранить текущую нормализацию `process_id`
- без `yaml_io` core снова будет зависеть от monolith I/O
- без `rel` изменится текст duplicate/error сообщений, а это уже behavior drift

Что **не** надо тянуть в helpers сейчас:
- `locate_flow_root`
- workplace-manifest discovery
- registry loading
- schema validation
- any runtime/session helpers

## Поведенческие инварианты первого среза
Новый core catalog обязан сохранить:
- точный порядок roots: `flow user -> flow custom -> project user -> project custom -> dist user -> dist custom -> project core -> dist core -> flow legacy_flat -> project legacy_flat -> dist legacy_flat`
- explicit `.yaml/.yml` path resolution
- те же `origin`, `root`, `catalog_role`, `pack_id`, `active`, `available`, `production_ready`
- ту же semantics для inactive official process с тем же `pack-activate` hint
- те же duplicate warnings и правило `process_override.reason`
- ту же legacy-flat поддержку

## Characterization tests
Минимальный обязательный regression-набор до и после переключения:

Catalog/resolve:
- `smoke_process_resolver_multiple_roots`
- `smoke_process_list_origin_filters`
- `smoke_process_id_stable_after_move`
- `smoke_process_root_collision_policy`
- `smoke_builtin_process_catalog`
- `smoke_builtin_process_pack_completeness`
- `smoke_pf_project_process_refs_follow_layout`
- `smoke_no_removed_process_refs`

Runtime safety:
- `smoke_runtime_host_poc`
- `smoke_long_lived_runtime`

Дополнительно нужны новые точечные characterization tests на core API:
- explicit path resolve сохраняет `origin/root/catalog_role`
- inactive official process даёт тот же `SystemExit` текст
- duplicate override warning не меняется
- flags `active/available/production_ready` для official pack не меняются

## Последовательность миграции
1. Завершить bootstrap prerequisite из Phase B: package shell и import path для `src/processforge_core`.
2. Добавить `common/*` и `process_catalog/*`.
3. Перенести catalog logic в core без изменения callers.
4. В `tools/processforge.py` заменить старые реализации на wrappers.
5. Переключить CLI callers, которые уже используют catalog seam:
   - `command_process_list`
   - `command_process_describe`
   - `command_task_create`
   - `process_definition_path`
   - `process_definition_exists`
   - `builtin_process_catalog_report`
   - `iter_process_definitions`
6. Переключить `tools/pf_runtime/host.py::resolved_process` на тот же core API.
7. Прогнать characterization.
8. Только после зелёного результата планировать отдельные Phase C/D срезы: validation/doctor/authoring.

## Вывод
Минимальный первый Process Definition extraction должен быть не “shared API set” из инвентаря, а **узкий `process_catalog` API**: один core package, один context boundary, legacy wrappers в `tools/processforge.py`, один runtime-host switch в `resolved_process(...)`. Это единственный малорискованный способ быстро получить общий CLI + runtime-host API и не затащить в canonical Core монолит, hooks, transport и runtime semantics.