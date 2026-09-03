# Adapter Patch Design

## Статус

`PASS` для Phase E при минимальном патче из трёх файлов: `src/processforge_core/process_catalog/service.py`, `src/processforge_core/process_catalog/__init__.py`, `tools/processforge.py`.

Цель патча: сделать публичными ровно три Core API-обёртки `official_process_definition_refs`, `process_root_candidates`, `process_root_yaml_files`, перевести legacy CLI wrappers на package-root imports и убрать прямой импорт `service as process_catalog_core`.

## Минимальный unified diff

```diff
diff --git a/src/processforge_core/process_catalog/service.py b/src/processforge_core/process_catalog/service.py
--- a/src/processforge_core/process_catalog/service.py
+++ b/src/processforge_core/process_catalog/service.py
@@
 def _official_process_definition_refs(
     context: ProcessCatalogContext,
     *,
     include_available: bool = False,
 ) -> list[ProcessDefinitionRef]:
@@
             )
     return entries


+def official_process_definition_refs(
+    context: ProcessCatalogContext,
+    *,
+    include_available: bool = False,
+) -> list[ProcessDefinitionRef]:
+    return _official_process_definition_refs(
+        context,
+        include_available=include_available,
+    )
+
+
 def _process_root_candidates(context: ProcessCatalogContext) -> list[tuple[Path, str, bool]]:
     candidates = [
         (context.flow_root / "processes" / "user", "user", False),
         (context.flow_root / "processes" / "custom", "custom", False),
         (context.project_root / "processes" / "user", "user", False),
@@
         seen.add(resolved)
         unique.append((path, origin, legacy))
     return unique


+def process_root_candidates(
+    context: ProcessCatalogContext,
+) -> list[tuple[Path, str, bool]]:
+    return _process_root_candidates(context)
+
+
 def _process_root_yaml_files(root: Path, *, legacy_flat: bool) -> list[Path]:
     if not root.is_dir():
         return []
     if legacy_flat:
         return sorted([*root.glob("*.yaml"), *root.glob("*.yml")])
     return sorted([path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in {".yaml", ".yml"}])


+def process_root_yaml_files(root: Path, *, legacy_flat: bool) -> list[Path]:
+    return _process_root_yaml_files(root, legacy_flat=legacy_flat)
+
+
 def process_catalog_entries(
     context: ProcessCatalogContext,
     *,
     strict: bool = False,
     include_available_official: bool = False,
diff --git a/src/processforge_core/process_catalog/__init__.py b/src/processforge_core/process_catalog/__init__.py
--- a/src/processforge_core/process_catalog/__init__.py
+++ b/src/processforge_core/process_catalog/__init__.py
@@
 from .models import ProcessCatalogContext, ProcessDefinitionRef
 from .service import (
     PROCESS_CATALOG_CLASSIFICATIONS,
+    official_process_definition_refs,
     process_catalog_entries,
     process_catalog_metadata,
     process_catalog_role,
     process_definition_exists,
+    process_root_candidates,
+    process_root_yaml_files,
     require_official_process_active,
     resolve_process_definition,
 )

 __all__ = [
     "ProcessCatalogContext",
     "ProcessDefinitionRef",
     "PROCESS_CATALOG_CLASSIFICATIONS",
+    "official_process_definition_refs",
     "process_catalog_entries",
     "process_catalog_metadata",
     "process_catalog_role",
     "process_definition_exists",
+    "process_root_candidates",
+    "process_root_yaml_files",
     "require_official_process_active",
     "resolve_process_definition",
 ]
diff --git a/tools/processforge.py b/tools/processforge.py
--- a/tools/processforge.py
+++ b/tools/processforge.py
@@
 from processforge_core.process_catalog import (
     PROCESS_CATALOG_CLASSIFICATIONS as CATALOG_PROCESS_CATALOG_CLASSIFICATIONS,
     ProcessCatalogContext,
     ProcessDefinitionRef,
+    official_process_definition_refs as catalog_official_process_definition_refs,
     process_catalog_metadata as catalog_process_catalog_metadata,
     process_catalog_entries as catalog_process_catalog_entries,
     process_catalog_role as catalog_process_catalog_role,
     process_definition_exists as catalog_process_definition_exists,
+    process_root_candidates as catalog_process_root_candidates,
+    process_root_yaml_files as catalog_process_root_yaml_files,
     require_official_process_active as catalog_require_official_process_active,
     resolve_process_definition as catalog_resolve_process_definition,
 )
-from processforge_core.process_catalog import service as process_catalog_core
 from processforge_subprocess import diagnostic_text, format_command as format_subprocess_command, run_command as run_subprocess_command
@@
 def official_process_definition_refs(
     project_root: Path,
     *,
     include_available: bool = False,
     workplace_manifest: Path | None = None,
 ) -> list[ProcessDefinitionRef]:
     context = _process_catalog_context(project_root, workplace_manifest=workplace_manifest)
-    return process_catalog_core._official_process_definition_refs(
+    return catalog_official_process_definition_refs(
         context,
         include_available=include_available,
     )


 def process_root_candidates(project_root: Path) -> list[tuple[Path, str, bool]]:
-    return process_catalog_core._process_root_candidates(_process_catalog_context(project_root))
+    return catalog_process_root_candidates(_process_catalog_context(project_root))


 def process_root_yaml_files(root: Path, *, legacy_flat: bool) -> list[Path]:
-    return process_catalog_core._process_root_yaml_files(root, legacy_flat=legacy_flat)
+    return catalog_process_root_yaml_files(root, legacy_flat=legacy_flat)
```

## Почему этого достаточно

- CLI-владение контекстом сохраняется: `_process_catalog_context(...)` в `tools/processforge.py` не меняется и по-прежнему строит `ProcessCatalogContext` из `project_root`, `flow_root`, `distribution_root` и `active_process_pack_ids(...)`.
- Сигнатуры сохраняются без изменений на обеих сторонах границы.
- В `service.py` не меняется логика `_official_pack_manifest_records`, `_official_process_definition_refs`, `_process_root_candidates`, `_process_root_yaml_files`; новые публичные функции только делегируют вызов.
- Упорядочивание кандидатов остаётся прежним: `flow user/custom -> project user/custom -> distribution user/custom -> project core -> distribution core -> legacy flat`.
- Поведение official-pack gating остаётся прежним: фильтрация по `active_official_pack_ids` и `include_available` остаётся внутри текущей helper-логики.
- Политика duplicate resolution остаётся прежней: `first wins`, те же warning-правила, тот же strict-режим.
- Поведение file walk остаётся прежним: `legacy_flat=True` использует только верхний уровень `glob`, иначе сохраняется рекурсивный обход `rglob`.
- Прямой импорт `service as process_catalog_core` убирается полностью.

## Границы и замечания

- `tools/processforge.py:14605-14606` остаётся без изменений и продолжает работать через тот же CLI wrapper `process_root_yaml_files(...)`.
- Переименовывать private helpers, переносить `_process_catalog_context()` в Core или менять внутренние call sites в этом патче не нужно.
- Патч минимален и закрывает ровно residual adapter debt, отмеченный в review: public package-root surface для трёх функций и удаление прямой зависимости CLI от service-модуля.