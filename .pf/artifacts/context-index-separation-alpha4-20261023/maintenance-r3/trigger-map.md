# Прочитанные triggers и граница worker

Источник: фактические Serena symbol/source excerpts `tools/processforge.py`, `resources/access.py` из frozen investigation, `resources/local_search.py`, `resources/catalog_read.py`, текущие CLI adapters и `docs/concepts/resource-search-index.md`. Это characterization baseline перед/во время независимой Main integration, не заявление о финальном состоянии чужих файлов.

| Путь/trigger | Baseline | Действие этого worker / передача |
| --- | --- | --- |
| `tools/pf_cli/commands/search_index.py`: explicit refresh/rebuild/tick | Прямой scoped ResourceSearchIndex вызов | Переведены через `.run_scoped()` общего owner; snapshot/guards/вывод сохранены |
| Тот же adapter: status/doctor | Только status | Поведение сохранено |
| Main workplace maintenance helper | Читает WorkplaceSearchCatalogReader, вызывает maintenance_tick, пишет latest report | Его exact maintenance shape переиспользован `.run()`; Main delegation — primary |
| Workplace initialization | Вызывает helper с reason `workplace-init` | Trigger R4 оценка и wiring — primary |
| Project initialization/repair/context refresh | Вызывает глобальный helper | По R2 должны только observe; чужая область primary/observation |
| Update apply/rollback | Вызывает helper с `update-apply` / `update-rollback` | По R4 сохранять dirty/reconciliation visibility без скрытой полной индексации; primary |
| Knowledge add-url/add-resource/index-refresh | Вызывает helper после registry/resource изменений | То же: mutation не превращается в необъявленный global build; primary |
| Template create, tool/mcp register, platform create/contract install | Вызывает helper после изменения ресурсов | То же; primary |
| ResourceSearchService readiness/search | Frozen investigation зафиксировал hidden maintenance | Удаление implicit side effects — observation worker |
| Future scheduler | В baseline нет отдельного delivered scheduler contract | Холодный callable другого worker должен вызывать тот же `.run()`; Runtime/timers не входят в revised scope |

Прямой вызов owning backend в своих tests используется только для conformance/query assertions. Нового источникового каталога, project enumeration, grant widening или indexing алгоритма не добавлено.
