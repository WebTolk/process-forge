# Инвентаризация legacy‑вызовов `process_catalog` (фаза E)

## Контекст
- Цель: перечислить 3 оставшихся обращения `tools/processforge.py` к приватным helper’ам `processforge_core.process_catalog.service`.
- Затронутые файлы: только читанные источники; код не изменялся.
- Публичный экспортный API пакета `processforge_core.process_catalog` подтверждён в `__init__.py`.

## Найденные legacy‑вызовы и карта

### 1) `process_catalog_core._official_process_definition_refs`
- **Локация в `tools/processforge.py`**: `official_process_definition_refs` (`~12564`)
  - Обёртка:
  - `official_process_definition_refs(project_root: Path, *, include_available: bool = False, workplace_manifest: Path | None = None) -> list[ProcessDefinitionRef]`
  - Вызов: `return process_catalog_core._official_process_definition_refs(context, include_available=include_available)`
- **Сигнатура приватного целевого API** (`service.py`):
  - `_official_process_definition_refs(context: ProcessCatalogContext, *, include_available: bool = False) -> list[ProcessDefinitionRef]`
- **Поведение**:
  - Формирует `ProcessCatalogContext`.
  - Читает манифесты активных/доступных офиц. пакетов.
  - Возвращает `ProcessDefinitionRef` с `origin="official"`, `active`, `available`, `pack_id`, `production_ready`.
  - Фильтрация по `include_available` для неактивных пакетов.
- **Все вызывающие стороны**:
  - Прямых внешних вызовов после этой обёртки в `tools/processforge.py` нет (вызов остаётся только в самой обёртке; сам вызов `command`-кодов к `official_process_definition_refs` не найден).
- **Публичный API‑вариант (замена)**:
  - Использовать `process_catalog_entries(context, include_available_official=...)` и, при необходимости, отфильтровать `entry.origin == "official"` по месту вызова.
  - Для единичного процесса: `resolve_process_definition(..., include_available_official=...)` (с тем же контекстом, где требуется).

### 2) `process_catalog_core._process_root_candidates`
- **Локация в `tools/processforge.py`**: `process_root_candidates` (`~12577`)
  - Обёртка:
  - `process_root_candidates(project_root: Path) -> list[tuple[Path, str, bool]]`
  - Вызов: `return process_catalog_core._process_root_candidates(_process_catalog_context(project_root))`
- **Сигнатура приватного целевого API** (`service.py`):
  - `_process_root_candidates(context: ProcessCatalogContext) -> list[tuple[Path, str, bool]]`
- **Поведение**:
  - Возвращает упорядоченный, дедуплицированный список кандидатов источников процессов:
    - `user/custom/core/legacy_flat` по `flow_root`, `project_root`, `distribution_root`, с флагом `legacy_flat`.
- **Все вызывающие стороны**:
  - Прямых вызовов `process_root_candidates(...)` после определения не найдено.
- **Публичный API‑вариант (замена)**:
  - Отдельного публичного API для кандидатов путей нет.
  - Эквивалент поведения доступен только через публичные высокоуровневые вызовы (например, `process_catalog_entries`), либо через новый adapter-level helper.

### 3) `process_catalog_core._process_root_yaml_files`
- **Локация в `tools/processforge.py`**: `process_root_yaml_files` (`~12581`)
  - Обёртка:
  - `process_root_yaml_files(root: Path, *, legacy_flat: bool) -> list[Path]`
  - Вызов: `return process_catalog_core._process_root_yaml_files(root, legacy_flat=legacy_flat)`
- **Сигнатура приватного целевого API** (`service.py`):
  - `_process_root_yaml_files(root: Path, *, legacy_flat: bool) -> list[Path]`
- **Поведение**:
  - Если `legacy_flat=False`: рекурсивный `rglob` по `*.yaml|*.yml`.
  - Если `legacy_flat=True`: только файлы одного уровня `*.yaml|*.yml`.
- **Все вызывающие стороны**:
  - Внутренне используется в `process_layout_checks` (`~14605`) для проверки резолва `core_root`:
    - `for path in process_root_yaml_files(core_root, legacy_flat=False): ...`
  - Прямых внешних вызовов обёртки кроме этого не найдено.
- **Публичный API‑вариант (замена)**:
  - Нет прямого публичного метода `ProcessCatalog` для выборки YAML по root.
  - Для бизнес‑проверок предпочтительнее опираться на `process_catalog_entries(..., strict=...)` и проверять `entry.path`, чем на прямой file-walk.

## Заключение по миграции
- Трёх legacy‑вызовов видно именно на уровне обёрток в `tools/processforge.py`; прямые вызовы приватных helper’ов модуля `service` за пределами этих трёх методов отсутствуют.
- Два из них (`_official_process_definition_refs`, `_process_root_candidates`) сейчас не имеют потребителей в `tools/processforge.py` помимо самих обёрток (мертвые или подготовленные для внешнего API).
- Публичная замена для `official`‑списка и разрешения процессов частично возможна через `process_catalog_entries` / `resolve_process_definition`; для candidate/file walking публичных эквивалентов в текущем пакете нет.