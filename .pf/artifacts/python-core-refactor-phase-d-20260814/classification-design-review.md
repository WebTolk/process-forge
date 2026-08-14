# Phase D review: classification/metadata

## Вердикт

### PASS
- Публичный package-root export для `PROCESS_CATALOG_CLASSIFICATIONS` и `process_catalog_metadata` корректен и согласован с уже существующим seam в `tools/processforge.py:45-54`: CLI сначала вызывает `_bootstrap_repo_src()`, потом импортирует `processforge_core.process_catalog`, так что ordering для нового re-export безопасен.
- Источник истины уже есть в `src/processforge_core/process_catalog/service.py:11-39`; перенос не требует новой core-логики, только публикации существующего API через `src/processforge_core/process_catalog/__init__.py`.
- Legacy callsites в разрешённом scope полностью подтверждены:
  - `process_catalog_metadata()` используется в `tools/processforge.py:14065`, `14115`, `14284`
  - `process_is_public_stable()` используется в `14116`, `14292`, `14347`
  - user-visible validation check `catalog classification valid` находится в `14119`
  - public-skip/report path для `INTERNAL_MAINTENANCE` находится в `14284-14287`
  - package stable check находится в `14344-14347`
- Риска цикла от re-export нет: `src/processforge_core/process_catalog/__init__.py` уже импортирует из `.service`, а `service.py` не импортирует package root обратно.

### CONDITIONS
- Реэкспорт должен идти через `processforge_core.process_catalog`, а не через прямой импорт `processforge_core.process_catalog.service`. Это принципиально для заявленного public API boundary.
- В `tools/processforge.py` Phase D должен ограничиться заменой локального drift на alias/wrapper поверх package-root API, без переписывания `validate_process_contract()` и `builtin_process_catalog_report()`. Иначе это уже не behavior-preserving срез.
- `process_is_public_stable()` лучше оставить в CLI. Это policy helper над metadata, а не часть shared catalog discovery surface.
- Нужно сохранить текущие user-visible тексты и семантику checks/reporting; полезного выигрыша от их изменения в Phase D нет.

### FAIL
- `.pf/artifacts/.../classification-inventory.md` задаёт слишком низкоуровневую границу: там предлагается импорт из `processforge_core.process_catalog.service`. Это противоречит более правильной цели из `classification-design.md` про package-root API.
- Текущий `src/processforge_core/process_catalog/__init__.py` ещё не экспортирует `PROCESS_CATALOG_CLASSIFICATIONS` и `process_catalog_metadata`, поэтому proposal пока не реализован и без этого Phase D нельзя считать завершённым.

## Исправленная граница Phase D
1. Добавить в `src/processforge_core/process_catalog/__init__.py` re-export:
   - `PROCESS_CATALOG_CLASSIFICATIONS`
   - `process_catalog_metadata`
   - обновить `__all__`
2. В `tools/processforge.py` расширить package-root import новыми alias.
3. Заменить локальные `PROCESS_CATALOG_CLASSIFICATIONS` и `process_catalog_metadata()` на делегирование в package-root API.
4. Не переносить в core:
   - `process_is_public_stable()`
   - `validate_process_contract()`
   - `builtin_process_catalog_report()`
   - любые doctor/report formatting changes
5. Не трогать `process_catalog_entries()/resolve_process_definition()` и остальную catalog/runtime/authoring логику.

## Итог
У Phase D статус `PASS WITH CONDITIONS`. Дизайн в `classification-design.md` по сути верный, но границу нужно формализовать жёстче: public seam только через package root, scope только `__init__` export + CLI deduplication, без расширения core и без изменения пользовательского поведения validation/reporting.