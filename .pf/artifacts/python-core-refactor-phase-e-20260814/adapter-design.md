# Дизайн адаптера Core API для Phase E

## Цель

Убрать из `tools/processforge.py` прямые вызовы приватных helper'ов `processforge_core.process_catalog.service`, не меняя текущее поведение CLI и не расширяя scope на validation/reporting, runtime state/event, MCP или hooks.

## Подтверждённое текущее состояние

- Публичный package-root seam уже существует для основных catalog API: `process_catalog_entries`, `resolve_process_definition`, `require_official_process_active`, `process_definition_exists`, `process_catalog_metadata`, `process_catalog_role` экспортируются из `src/processforge_core/process_catalog/__init__.py:1-16`.
- Остаточный boundary debt локализован в одном месте: `tools/processforge.py:56` импортирует `service as process_catalog_core`, а `tools/processforge.py:12564-12582` вызывает три приватных helper'а:
  - `_official_process_definition_refs(...)`
  - `_process_root_candidates(...)`
  - `_process_root_yaml_files(...)`
- Контекст для Core уже собирается на стороне CLI в `tools/processforge.py:12457-12471` через `ProcessCatalogContext(project_root, flow_root, distribution_root, active_official_pack_ids)`.
- Эти helper'ы реально живут в Core и уже имеют стабильные по смыслу сигнатуры в `src/processforge_core/process_catalog/service.py:81-151`.

## Минимальный публичный Core API

Предлагаемый новый публичный слой в `processforge_core.process_catalog`:

```python
def official_process_definition_refs(
    context: ProcessCatalogContext,
    *,
    include_available: bool = False,
) -> list[ProcessDefinitionRef]: ...

def process_root_candidates(
    context: ProcessCatalogContext,
) -> list[tuple[Path, str, bool]]: ...

def process_root_yaml_files(
    root: Path,
    *,
    legacy_flat: bool,
) -> list[Path]: ...
```

Пакетный экспорт в `src/processforge_core/process_catalog/__init__.py` должен быть расширен этими тремя именами. Реализация должна остаться в `service.py`; минимальный вариант - добавить публичные функции-алиасы без подчёркивания поверх текущих реализаций и реэкспортировать их через package root.

## Владение контекстом и путями

- `ProcessCatalogContext` должен остаться входом публичного Core API для всего, что зависит от `project_root`, `flow_root`, `distribution_root` и `active_official_pack_ids`.
- Построение `ProcessCatalogContext` должно остаться в CLI-слое (`tools/processforge.py:12457-12471`), потому что именно CLI знает, как выводить `workplace_manifest` и `active_process_pack_ids(...)`.
- `process_root_yaml_files(root, legacy_flat=...)` корректно оставлять path-level API без `ProcessCatalogContext`: helper чисто файловый и не тянет workplace/project policy.

Это сохраняет текущую границу ответственности: Core каталогизирует по готовому контексту, CLI собирает окружение.

## Поведенческие инварианты, которые нельзя менять

- Порядок кандидатов в каталоге должен остаться прежним: `service.py:121-143` сначала `flow/user`, `flow/custom`, затем `project/user`, `project/custom`, затем `distribution/user`, `distribution/custom`, потом `project/core`, `distribution/core`, и только после этого legacy flat roots.
- Official pack entries должны по-прежнему вставляться перед первым `core` root, но после всех `user/custom` roots (`service.py:185-214`). Это сохраняет текущий override priority.
- Duplicate resolution должна остаться first-wins с теми же warning-правилами (`service.py:164-183`).
- `process_root_yaml_files()` должен сохранить текущую семантику:
  - `legacy_flat=True` -> только верхний уровень `*.yaml|*.yml`
  - `legacy_flat=False` -> рекурсивный обход
- `official_process_definition_refs(..., include_available=...)` должен сохранить текущую фильтрацию по `active_official_pack_ids` и `provides.processes` (`service.py:81-119`).

## Совместимость и адаптерный шов

Минимально безопасный переход:

- Не менять внешние CLI-сигнатуры `official_process_definition_refs(project_root, ..., workplace_manifest=None)`, `process_root_candidates(project_root)`, `process_root_yaml_files(root, ..., legacy_flat)`.
- Внутри `tools/processforge.py` перевести их с приватных вызовов на публичные импорты package root.
- Удалить импорт `from processforge_core.process_catalog import service as process_catalog_core`.
- Оставить все остальные wrapper'ы в CLI без изменений, чтобы не ломать существующие call sites внутри `tools/processforge.py`.

Итоговый effect: Core surface становится публично полным для catalog/resolve adapter bridge, а CLI остаётся backward-compatible для текущих внутренних пользователей.

## Риск импортов и циклов

Риск цикла низкий, если:

- новые публичные функции остаются определёнными в `service.py`;
- `__init__.py` только реэкспортирует их;
- `service.py` не начинает импортировать package root.

Не нужно переносить `_process_catalog_context()` или workplace resolution в Core: это уже увеличит coupling и создаст риск обратной зависимости Core -> CLI policy.

## Рекомендуемое решение

Для Phase E достаточно:

1. Поднять три helper'а в публичный Core API с теми же по смыслу сигнатурами.
2. Реэкспортировать их из `processforge_core.process_catalog`.
3. Перевести `tools/processforge.py:12564-12582` на package-root imports.
4. Не трогать ordering, duplicate policy, active-pack gating и CLI-level context construction.

Это минимальный behavior-preserving дизайн, который закрывает residual adapter debt из adjudication Phase D, не расширяя публичную поверхность дальше необходимого.