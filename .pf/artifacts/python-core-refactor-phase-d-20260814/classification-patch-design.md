# Phase D: classification patch design

## Целевой unified diff

```diff
--- a/src/processforge_core/process_catalog/__init__.py
+++ b/src/processforge_core/process_catalog/__init__.py
@@
 from .models import ProcessCatalogContext, ProcessDefinitionRef
 from .service import (
+    PROCESS_CATALOG_CLASSIFICATIONS,
     process_catalog_entries,
+    process_catalog_metadata,
     process_catalog_role,
     process_definition_exists,
     require_official_process_active,
     resolve_process_definition,
 )
@@
 __all__ = [
     "ProcessCatalogContext",
     "ProcessDefinitionRef",
+    "PROCESS_CATALOG_CLASSIFICATIONS",
     "process_catalog_entries",
+    "process_catalog_metadata",
     "process_catalog_role",
     "process_definition_exists",
     "require_official_process_active",
     "resolve_process_definition",
 ]
--- a/tools/processforge.py
+++ b/tools/processforge.py
@@
 from processforge_core.process_catalog import (
+    PROCESS_CATALOG_CLASSIFICATIONS as CATALOG_PROCESS_CATALOG_CLASSIFICATIONS,
     ProcessCatalogContext,
     ProcessDefinitionRef,
+    process_catalog_metadata as catalog_process_catalog_metadata,
     process_catalog_entries as catalog_process_catalog_entries,
     process_catalog_role as catalog_process_catalog_role,
     process_definition_exists as catalog_process_definition_exists,
     require_official_process_active as catalog_require_official_process_active,
     resolve_process_definition as catalog_resolve_process_definition,
@@
-PROCESS_CATALOG_CLASSIFICATIONS = {
-    "PUBLIC_STABLE",
-    "PUBLIC_EXPERIMENTAL",
-    "INTERNAL_MAINTENANCE",
-    "EXAMPLE_ONLY",
-    "DEPRECATED",
-}
+PROCESS_CATALOG_CLASSIFICATIONS = CATALOG_PROCESS_CATALOG_CLASSIFICATIONS
@@
 def process_catalog_metadata(process: dict[str, Any]) -> dict[str, Any]:
-    catalog = process.get("catalog") if isinstance(process.get("catalog"), dict) else {}
-    status = str(process.get("status") or "draft")
-    classification = str(catalog.get("classification") or "").upper()
-    if classification not in PROCESS_CATALOG_CLASSIFICATIONS:
-        if status == "active":
-            classification = "PUBLIC_STABLE"
-        elif status == "experimental":
-            classification = "PUBLIC_EXPERIMENTAL"
-        elif status == "internal":
-            classification = "INTERNAL_MAINTENANCE"
-        elif status == "deprecated":
-            classification = "DEPRECATED"
-        else:
-            classification = "PUBLIC_EXPERIMENTAL"
-    public_surface = catalog.get("public_surface", process.get("public_surface", classification != "INTERNAL_MAINTENANCE"))
-    return {"classification": classification, "public_surface": bool(public_surface), "status": status}
+    return catalog_process_catalog_metadata(process)
```

## Граница патча

- `process_is_public_stable()` оставить в `tools/processforge.py`. Review помечает его как CLI policy helper, а не часть shared catalog API.
- `validate_process_contract()` и `builtin_process_catalog_report()` не переписывать. Они уже используют нужный seam через локальные имя/вызов, а Phase D требует только убрать drift-реализацию.
- `from processforge_core.process_catalog import service as process_catalog_core` не удалять. Этот импорт всё ещё нужен в `tools/processforge.py:12569`, `12576`, `12580` для других CLI-wrapper’ов.
- `src/processforge_core/process_catalog/service.py` не менять: источник истины уже находится там.

## Почему это проходит review

- Выполняет `PASS WITH CONDITIONS` из review: public seam идёт только через `processforge_core.process_catalog`, без прямого consumer-доступа к `processforge_core.process_catalog.service`.
- Убирает локальный drift в `tools/processforge.py:14036-14061` ровно через alias/wrapper, без изменения user-visible check/report text.
- Сохраняет текущее поведение для всех подтверждённых call-site:
  - `process_catalog_metadata()` в `14065`, `14115`, `14284`
  - `process_is_public_stable()` в `14116`, `14292`, `14347`
  - `catalog classification valid` в `14119`
  - public-skip path в `14285-14287`
  - package stable check в `14344-14347`

## Критерий готовности

- package-root экспортирует `PROCESS_CATALOG_CLASSIFICATIONS` и `process_catalog_metadata`
- CLI больше не владеет собственной копией classification/metadata logic
- поведение validation/reporting/import bootstrap не меняется