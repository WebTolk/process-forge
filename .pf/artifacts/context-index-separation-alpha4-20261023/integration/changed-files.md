# Изменённые файлы integration contribution

Созданы:

- `tests/context_index_separation/conftest.py` — первым изменением добавлен bootstrap `tools`/`src`.
- `tests/context_index_separation/test_integration.py` — реальные registry/Main/Core fixtures, access/error checks и характеристика чтений.
- `tests/context_index_separation/test_backend_contract.py` — SQLite metadata/errors, конкуренция writer/readers и crash/retry.

Изменены:

- `tools/smoke_project_init_local_search_mcp.py` — явное обслуживание собственного workplace fixture перед ожиданием physical catalogue/report.
- `tools/smoke_resource_search_snapshot_composition.py` — seam наблюдения, запрет hidden maintenance, согласованная пагинация успешного fixture и строгие error/status assertions.
- `docs/concepts/project-context-snapshot.md`.
- `docs/concepts/resource-search-index.md`.
- `docs/ru/concepts/project-context-snapshot.md`.
- `docs/ru/concepts/resource-search-index.md`.

Учёт и evidence:

- `.pf/logs/context-index-alpha4-integration-20261023.md`.
- Артефакты этой integration-области: `stdlib-results.json`, `final-verification.json`, сохранённые результаты первоначальных неудачных прогонов, `changed-files.md`, `change-summary.md`, `qa-handoff.md`.
- Собственные scratch probe и `run-stdlib.py` сохранены как воспроизводимое evidence; начальный недоступный временный каталог сохранён после отказа автоматической проверки очистки.

Продуктовые implementation owners, Git, версии, checksums, release и PF lifecycle не изменялись. Разрешённые `smoke_project_context_snapshot_lock_model.py` и `smoke_project_resource_narrowing_search.py` прочитаны и оставлены без изменений: у них не потребовалась замена предположения об implicit indexing.
