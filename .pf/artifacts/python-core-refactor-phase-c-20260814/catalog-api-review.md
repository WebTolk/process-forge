# Review: Catalog API Phase C

## Вердикт

`pass_with_conditions`

Идея узкого Phase C с выносом только catalog/resolve seam подтверждается исходниками, но текущий `catalog-api-design.md` всё ещё неточен в трёх местах:

- он всё ещё недооценивает фактические зависимости catalog-логики;
- он не фиксирует реальный порядок каталога с вставкой `official` перед первым `core`;
- формулировка про “общий CLI/runtime API” верна только для seam `resolve_process_definition`, а не для всего runtime-host surface.

Расширять срез до `host` payload/state/event logic не обосновано. По текущему коду это уже другой предметный слой.

## Что подтверждено по исходнику

- Реальный общий seam сейчас один: `tools/pf_runtime/host.py:103-123` вызывает `core.resolve_process_definition(...)`, а CLI использует тот же резолвер через `tools/processforge.py:12693-12772`, `14167-14647`, `19402-19411`.
- `project_state_payload`, `work_state_payload`, `resolve_payload`, `ingest_event`, `active_execution_records` и `declared_stage_obligations` в `tools/pf_runtime/host.py` не являются catalog API. Они только потребляют результат резолва или вообще работают с event/session/projection state.
- `src/processforge_core/bootstrap.py:17-79` не должен становиться зависимостью нового catalog core. Его роль сейчас только в том, чтобы добавить `src`/`tools` в `sys.path`, загрузить legacy core и импортировать runtime adapters.

## Критичные замечания к текущему дизайну

- В дизайне пропущена зависимость `process_catalog_role()` от `process_catalog_metadata()` и `PROCESS_CATALOG_CLASSIFICATIONS` (`tools/processforge.py:12449-12458`, `14202-14220`). Без этого `catalog_role` начнёт дрейфовать для `internal`/`deprecated`.
- В дизайне не зафиксирована зависимость official-ветки от тривиальной нормализации списков `as_list()` (`tools/processforge.py:12565`, `12587`, `11451`/`12989`). Это можно инлайнить, но нельзя игнорировать.
- Самая важная поведенческая деталь: фактический порядок не равен списку roots из дизайна. В `process_catalog_entries()` official entries вставляются один раз перед первым `core` root (`tools/processforge.py:12659-12667`). Значит инвариант порядка сейчас такой:
  `flow user -> flow custom -> project user -> project custom -> dist user -> dist custom -> official -> project core -> dist core -> flow legacy_flat -> project legacy_flat -> dist legacy_flat`
- Ошибка для неактивного official process должна сохраниться побайтно по смыслу, включая `pack-activate` hint (`tools/processforge.py:12733-12746`, `12748-12767`).
- В рамках разрешённого scope не доказано, что CLI import path для нового `src/processforge_core/...` уже полностью готов. Для runtime prerequisite виден в `bootstrap.py`; для CLI это надо считать условием из Phase B, а не доказанным фактом.

## Риск модульной идентичности

- Риск реальный, но локальный: runtime bootstrap кэширует legacy core под двумя именами, `processforge_core._legacy_processforge` и `processforge` (`src/processforge_core/bootstrap.py:12-58`).
- Поэтому нельзя оставлять вторую независимую реализацию `ProcessDefinitionRef` в `tools/processforge.py`. Должен быть один владелец типа: `src/processforge_core/process_catalog/models.py`, а legacy-модуль должен только реэкспортировать alias/wrapper.
- В разрешённых файлах не найдено `isinstance(..., ProcessDefinitionRef)`, поэтому при структурном использовании `.path/.process` риск управляемый.

## Исправленная минимальная граница реализации

Публичное core API:

- `ProcessDefinitionRef`
- `ProcessCatalogContext`
- `process_catalog_role(...)`
- `process_catalog_entries(...)`
- `resolve_process_definition(...)`
- `process_definition_exists(...)`
- `require_official_process_active(...)`

Обязательные private helpers внутри того же core-среза:

- `process_catalog_metadata(...)`
- `process_override_declared(...)`
- `official_pack_manifest_records(...)`
- `_official_process_definition_refs(...)`
- `_process_root_yaml_files(...)`

Минимальные инфраструктурные helpers, без которых перенос будет неполным:

- `safe_id`
- `rel`
- `load_yaml_document`
- `yaml_error`
- `read_yaml_file`
- эквивалент `as_list`

Что должно остаться в legacy adapter layer:

- `locate_flow_root`
- `ROOT`/distribution root resolution
- `resolve_project_workplace_manifest(...)`
- `active_process_pack_ids(...)`
- все `host` payload/event/session/projection функции
- весь doctor/authoring/validation/route-handoff слой

## Итог

Правильный Phase C boundary уже уже, чем предложено в inventory, и чуть шире, чем перечислено в дизайне: переносить надо только catalog/resolve API, но перенос должен сохранить реальные зависимости и фактический порядок каталога, включая вставку `official` перед `core`. Если CLI wrappers и `host.resolved_process()` начнут вызывать один и тот же новый `process_catalog.resolve_process_definition(...)`, то CLI и runtime действительно будут использовать один API seam. Больше этого текущий исходник не подтверждает, и расширять объём работ на `host` state/payload/event surface сейчас не следует.