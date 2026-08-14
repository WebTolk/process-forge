# Phase D code review

## Вердикт
`FAIL`

## PASS
- Источник классификационной метадаты действительно сведён в `src/processforge_core/process_catalog/service.py:11-39`, а package-root реэкспорт оформлен в `src/processforge_core/process_catalog/__init__.py:2-17`.
- CLI-совместимость для самой Phase D части сохранена: `tools/processforge.py:14038-14047` оставляет прежние имена `PROCESS_CATALOG_CLASSIFICATIONS`, `process_catalog_metadata()` и `process_is_public_stable()`, при этом `process_catalog_metadata()` уже просто делегирует в package-root alias.
- Наблюдаемого legacy fallback для вычисления classification/status/public_surface в CLI больше нет: логика живёт в `service.py`, а не дублируется в `tools/processforge.py`.
- Downstream-поведение в проверках и отчёте сохранено:
  - `catalog classification valid` остаётся в `tools/processforge.py:14095-14101`;
  - пропуск `INTERNAL_MAINTENANCE` для public-report сохраняется в `tools/processforge.py:14266-14284`;
  - проверка `stable process is public stable` сохраняется в `tools/processforge.py:14321-14328`;
  - печать summary/doctor не меняет ожидаемую семантику в `tools/processforge.py:14335-14355`.
- По разрешённому срезу импортный порядок безопасен: `_bootstrap_repo_src()` выполняется до импортов `processforge_core...` (`tools/processforge.py:33-57`), `process_catalog.__init__` импортирует `.service` и `.models`, а `service.py` импортирует только `.models`; явного цикла в этом контуре не видно.

## FAIL
- Критерий “CLI consumer aliases используют только package-root API” не выполнен. `tools/processforge.py:56` всё ещё импортирует внутренний модуль `processforge_core.process_catalog.service as process_catalog_core`.
- Критерий “no scope expansion” тоже не выполнен: CLI продолжает ходить в приватные `_...` helper'ы сервиса:
  - `tools/processforge.py:12571-12574` -> `process_catalog_core._official_process_definition_refs(...)`
  - `tools/processforge.py:12577-12582` -> `process_catalog_core._process_root_candidates(...)` и `_process_root_yaml_files(...)`
- Это оставляет boundary leak в сторону внутренней service-реализации: классификационная часть переведена на package-root, но весь CLI-контракт не замкнут на публичный surface `processforge_core.process_catalog`.

## Условие закрытия
- Для закрытия Phase D без оговорок CLI должен перестать импортировать `process_catalog.service` напрямую и перестать вызывать `_official_process_definition_refs`, `_process_root_candidates`, `_process_root_yaml_files` из `tools/processforge.py`.
- После этого можно будет засчитать и “only package-root API”, и “no scope expansion”, при сохранении уже достигнутой совместимости классификационных проверок и отчётов.