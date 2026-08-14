# Phase D: дизайн переноса classification/metadata на shared `process_catalog` API

## Решение

Минимальный behavior-preserving Phase D не требует менять реализацию каталога в `src/processforge_core/process_catalog/service.py`: нужный shared slice уже существует в `service.py:11-44`. Достаточно опубликовать его через package-root API и переключить validation/reporting surface legacy CLI с локальной копии на этот seam.

Это закрывает условие из Phase C review про drift в `tools/processforge.py:14036-14066`, не затрагивая authoring validation, runtime state/event, MCP, hooks и без расширения core-логики сверх уже существующей.

## Подтвержденные consumer'ы

- `tools/processforge.py:14064-14066` `process_is_public_stable()` зависит от metadata.
- `tools/processforge.py:14106-14240` `validate_process_contract()` использует metadata для `stable`, `hard`, companion strictness и classification check.
- `tools/processforge.py:14265-14351` `builtin_process_catalog_report()` использует metadata для public filter, summary counters, report rows и package stable checks.
- В разрешённом scope других call-site для локального `process_catalog_metadata()` нет: только `14065`, `14115`, `14284`.
- Других call-site для `process_is_public_stable()` тоже нет: только `14116`, `14292`, `14347`.

## Минимальная граница изменений

- `src/processforge_core/process_catalog/service.py`
  - Не менять семантику.
  - Оставить единым источником истины `PROCESS_CATALOG_CLASSIFICATIONS` (`11-17`) и `process_catalog_metadata()` (`28-44`).

- `src/processforge_core/process_catalog/__init__.py`
  - Добавить re-export `process_catalog_metadata`.
  - Добавить re-export `PROCESS_CATALOG_CLASSIFICATIONS`.
  - Обновить `__all__`, чтобы package-root API был явным и симметричным уже существующим `process_catalog_entries`, `process_catalog_role`, `resolve_process_definition`.

- `tools/processforge.py:45-54`
  - Расширить import из `processforge_core.process_catalog` новыми alias, по тому же паттерну, что уже используется для `entries/role/resolve/exists/require_official_process_active`.

- `tools/processforge.py:14036-14061`
  - Убрать локальную реализацию-drift.
  - Самый малорисковый вариант:
    - `PROCESS_CATALOG_CLASSIFICATIONS = CATALOG_PROCESS_CATALOG_CLASSIFICATIONS`
    - `def process_catalog_metadata(...): return catalog_process_catalog_metadata(process)`
  - Это сохраняет текущие downstream call-site и не меняет тексты/форму doctor-report checks.

## Почему именно так

- В `tools/processforge.py:45-54` уже существует package-root seam для shared catalog API. Metadata/classification надо проводить через тот же публичный вход, а не через `service` internals.
- `process_catalog_role()` уже оформлен как тонкий CLI-wrapper в `tools/processforge.py:12472-12473`. Такой же подход для metadata даёт минимальный diff и низкий риск.
- Экспорт константы лучше, чем переписывание `validate_process_contract()` на новый текст check: строка `14119` сейчас user-visible, и нет пользы менять её поведение/формулировку в Phase D.
- Перенос `process_is_public_stable()` в core сейчас не нужен. Это не catalog discovery API, а CLI policy helper поверх shared metadata. Его можно оставить локальным.

## Импорты и риск циклов

- Подтверждённый Phase C вывод остаётся валидным: `src/processforge_core/process_catalog/service.py:6-8` зависит только от `processforge_core.common` и локальных моделей, без зависимости на `tools`.
- Re-export из `src/processforge_core/process_catalog/__init__.py:1-18` не создаёт новый цикл: `__init__` уже импортирует из `.service`, а `service.py` не импортирует package-root обратно.
- Нельзя делать обратный перенос validation/reporting helper'ов в core: это уже расширило бы границу и повысило бы риск core-to-tools coupling.
- Нежелательно использовать `from processforge_core.process_catalog import service as ...` для metadata/classification consumer'ов: это оставляет package-root API неполным и закрепляет CLI за internal module shape.

## Что не входит в Phase D

- Любые изменения `process_catalog_entries()`, `resolve_process_definition()`, official pack logic и duplicate/override warnings.
- Любые изменения authoring validation вне classification/metadata seam.
- Любые изменения runtime host, state/event, hooks, MCP, bootstrap/launcher поведения.
- Любые изменения формата `builtin_process_catalog_report()`.

## Тесты

- Import seam smoke:
  - `python tools/processforge.py ...` по-прежнему импортирует `processforge_core.process_catalog` после `_bootstrap_repo_src()`; новые exports не ломают существующий startup path.
  - Прямой import `process_catalog_metadata` и `PROCESS_CATALOG_CLASSIFICATIONS` из package root проходит.

- Metadata parity:
  - Для dict без `catalog.classification` fallback остаётся прежним:
    - `active -> PUBLIC_STABLE`
    - `experimental -> PUBLIC_EXPERIMENTAL`
    - `internal -> INTERNAL_MAINTENANCE`
    - `deprecated -> DEPRECATED`
    - любой другой/пустой status -> `PUBLIC_EXPERIMENTAL`
  - Явный `catalog.classification` по-прежнему upper-case нормализуется.
  - Явный `catalog.public_surface` и legacy `public_surface` по-прежнему приоритетны так же, как сейчас.

- Validation/reporting regression:
  - `process_is_public_stable()` остаётся true только при `classification == PUBLIC_STABLE`, `public_surface == True`, `status == active`.
  - `validate_process_contract()` сохраняет `hard = strict or stable`.
  - `builtin_process_catalog_report(public=True)` по-прежнему пропускает `INTERNAL_MAINTENANCE` через skip-path `14285-14287`.
  - Package check `stable process is public stable` в `14344-14347` сохраняет текущую семантику.

- Non-regression boundary:
  - Нет новых импортов из `tools` в `src/processforge_core/process_catalog/*`.
  - Нет новых прямых consumer'ов `service` internals для metadata/classification в CLI.

## Критерий готовности Phase D

- Legacy CLI больше не владеет собственной реализацией classification fallback logic.
- Validation/reporting surface потребляет shared metadata/classification API через package-root `processforge_core.process_catalog`.
- Поведение doctor/reporting и import/bootstrap path не меняются.
- Граница Phase C сохраняется: core остаётся без compile-time зависимости на `tools`.