# Review: Phase E adapter design

## Вердикт
**PASS с условиями.** Предложенный дизайн соответствует исходникам и закрывает ровно тот остаточный adapter debt, который реально подтверждён в коде: приватный импорт `service as process_catalog_core` в `tools/processforge.py:56` и три обращения к `_official_process_definition_refs`, `_process_root_candidates`, `_process_root_yaml_files` в `tools/processforge.py:12564-12582`.

## Подтверждено по исходникам
- Сигнатуры трёх целевых Core-функций в дизайне совпадают по смыслу с текущими реализациями в `src/processforge_core/process_catalog/service.py:81-151`:
  - `official_process_definition_refs(context, *, include_available=False)` <- текущая `_official_process_definition_refs(...)` в `service.py:81-118`
  - `process_root_candidates(context)` <- текущая `_process_root_candidates(...)` в `service.py:121-143`
  - `process_root_yaml_files(root, *, legacy_flat)` <- текущая `_process_root_yaml_files(...)` в `service.py:146-151`
- Владение `ProcessCatalogContext` корректно оставлено за CLI. Контекст собирается в `tools/processforge.py:12457-12471` из `project_root`, `flow_root`, `distribution_root` и `active_process_pack_ids(...)`. Перенос этой логики в Core исходниками не требуется.
- Порядок каталога в дизайне описан верно и менять его нельзя: `flow user/custom` -> `project user/custom` -> `distribution user/custom` -> `project core` -> `distribution core` -> legacy flat, см. `service.py:121-143`.
- Вставка official entries перед первым `core` root и после всех `user/custom` roots подтверждена в `service.py:185-193`.
- Политика duplicate resolution действительно `first wins`; strict лишь добавляет warning, а не меняет winner, см. `service.py:164-183`, `214-215`.
- Семантика `process_root_yaml_files()` подтверждена: `legacy_flat=True` только верхний уровень, иначе рекурсивный обход, см. `service.py:146-151`.
- Риск цикла импорта низкий, если реализация останется в `service.py`, а `__init__.py` только реэкспортирует имена. Сейчас `service.py` импортирует только `processforge_core.common` и `.models`, см. `service.py:1-8`, и не зависит от package root.
- Публичная поверхность сейчас узкая: в `src/processforge_core/process_catalog/__init__.py:1-22` этих трёх имён пока нет. Добавление только их выглядит обоснованным; расширять экспорт дальше исходники не требуют.

## Условия
- Не раскрывать дополнительные внутренние helper'ы вроде `_official_pack_manifest_records`; источник подтверждает необходимость только трёх функций.
- Не удалять CLI-обёртки только потому, что внутри этого файла у `official_process_definition_refs(...)` и `process_root_candidates(...)` не найдено текущих downstream-вызовов. Assignment прямо запрещает dead-code removal без необходимости, а внешний контракт `tools/processforge.py` по исходникам не опровергнут.
- `process_root_yaml_files(...)` в CLI точно остаётся совместимым wrapper’ом, потому что у него есть живой внутренний потребитель в `tools/processforge.py:14605-14606`.
- Для Phase E достаточно заменить приватный импорт/вызовы на package-root API; перенос workplace resolution или `_process_catalog_context()` в Core был бы лишним расширением scope.

## Fail
- Fail-замечаний по самому дизайну нет. Единственная обязательная дисциплина внедрения: не допустить обратного импорта `service.py -> processforge_core.process_catalog`, иначе будет создан искусственный цикл, которого сейчас нет.