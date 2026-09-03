# Catalog API Patch Correction

## Вывод

Подтверждённый блокер реальный: при прямом запуске `python tools/processforge.py ...` интерпретатор видит `tools/` как `sys.path[0]`, но не видит `src/`, поэтому первый же `from processforge_core...` упадёт с `ModuleNotFoundError`. Исправление должно быть встроено в сам CLI-скрипт, а не оставлено как внешний prerequisite. При этом `src/processforge_core/bootstrap.py` менять не нужно: он уже правильно обслуживает runtime-путь и alias legacy-core.

Ниже исправленный полный unified diff. Он сохраняет принятый bounded Phase C срез, добавляет безопасный bootstrap только для прямого CLI, не вводит цикл через `bootstrap.py` и оставляет одного владельца `ProcessDefinitionRef`.

## Исправленный unified diff

```diff
diff --git a/src/processforge_core/common/__init__.py b/src/processforge_core/common/__init__.py
new file mode 100644
--- /dev/null
+++ b/src/processforge_core/common/__init__.py
@@
+from .ids import safe_id
+from .paths import rel
+from .yaml_io import load_yaml_document, read_yaml_file, yaml_error
+
+__all__ = [
+    "load_yaml_document",
+    "read_yaml_file",
+    "rel",
+    "safe_id",
+    "yaml_error",
+]

diff --git a/src/processforge_core/common/ids.py b/src/processforge_core/common/ids.py
new file mode 100644
--- /dev/null
+++ b/src/processforge_core/common/ids.py
@@
+from __future__ import annotations
+
+import re
+
+
+def safe_id(value: str, default: str = "project") -> str:
+    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
+    return cleaned or default

diff --git a/src/processforge_core/common/paths.py b/src/processforge_core/common/paths.py
new file mode 100644
--- /dev/null
+++ b/src/processforge_core/common/paths.py
@@
+from __future__ import annotations
+
+from pathlib import Path
+
+
+def rel(path: Path, root: Path) -> str:
+    try:
+        return path.relative_to(root).as_posix()
+    except ValueError:
+        return path.as_posix()

diff --git a/src/processforge_core/common/yaml_io.py b/src/processforge_core/common/yaml_io.py
new file mode 100644
--- /dev/null
+++ b/src/processforge_core/common/yaml_io.py
@@
+from __future__ import annotations
+
+import re
+from pathlib import Path
+from typing import Any
+
+
+def _parse_scalar(value: str) -> Any:
+    value = value.strip()
+    if not value:
+        return ""
+    if value in {"true", "True"}:
+        return True
+    if value in {"false", "False"}:
+        return False
+    if value in {"null", "Null", "NULL", "~"}:
+        return None
+    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
+        return value[1:-1]
+    if re.fullmatch(r"-?\d+", value):
+        try:
+            return int(value)
+        except ValueError:
+            return value
+    return value
+
+
+def _parse_simple_yaml(text: str) -> dict[str, Any]:
+    root: dict[str, Any] = {}
+    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
+    for raw_line in text.splitlines():
+        line = raw_line.split("#", 1)[0].rstrip()
+        if not line.strip():
+            continue
+        indent = len(line) - len(line.lstrip(" "))
+        stripped = line.strip()
+        if stripped.startswith("- "):
+            continue
+        if ":" not in stripped:
+            continue
+        key, value = stripped.split(":", 1)
+        key = key.strip()
+        while stack and indent <= stack[-1][0]:
+            stack.pop()
+        parent = stack[-1][1] if stack else root
+        if value.strip() == "":
+            child: dict[str, Any] = {}
+            parent[key] = child
+            stack.append((indent, child))
+        else:
+            parent[key] = _parse_scalar(value)
+    return root
+
+
+def load_yaml_document(path: Path) -> dict[str, Any]:
+    if not path.is_file():
+        return {}
+    text = path.read_text(encoding="utf-8", errors="replace")
+    try:
+        import yaml  # type: ignore
+
+        data = yaml.safe_load(text)
+        return data if isinstance(data, dict) else {}
+    except ModuleNotFoundError:
+        return _parse_simple_yaml(text)
+    except Exception as exc:
+        return {"__yaml_error__": f"{exc.__class__.__name__}: {exc}"}
+
+
+def yaml_error(data: Any) -> str | None:
+    if isinstance(data, dict) and isinstance(data.get("__yaml_error__"), str):
+        return str(data["__yaml_error__"])
+    return None
+
+
+def read_yaml_file(path: Path) -> dict[str, Any]:
+    data = load_yaml_document(path)
+    error = yaml_error(data)
+    if error:
+        raise SystemExit(f"FAIL: {path} is invalid YAML: {error}")
+    return data

diff --git a/src/processforge_core/process_catalog/__init__.py b/src/processforge_core/process_catalog/__init__.py
new file mode 100644
--- /dev/null
+++ b/src/processforge_core/process_catalog/__init__.py
@@
+from .models import ProcessCatalogContext, ProcessDefinitionRef
+from .service import (
+    process_catalog_entries,
+    process_catalog_role,
+    process_definition_exists,
+    require_official_process_active,
+    resolve_process_definition,
+)
+
+__all__ = [
+    "ProcessCatalogContext",
+    "ProcessDefinitionRef",
+    "process_catalog_entries",
+    "process_catalog_role",
+    "process_definition_exists",
+    "require_official_process_active",
+    "resolve_process_definition",
+]

diff --git a/src/processforge_core/process_catalog/models.py b/src/processforge_core/process_catalog/models.py
new file mode 100644
--- /dev/null
+++ b/src/processforge_core/process_catalog/models.py
@@
+from __future__ import annotations
+
+from dataclasses import dataclass
+from pathlib import Path
+from typing import Any
+
+
+@dataclass(frozen=True)
+class ProcessCatalogContext:
+    project_root: Path
+    flow_root: Path
+    distribution_root: Path
+    active_official_pack_ids: frozenset[str]
+
+
+@dataclass
+class ProcessDefinitionRef:
+    process_id: str
+    path: Path
+    process: dict[str, Any]
+    origin: str
+    root: Path
+    catalog_role: str
+    warnings: list[str]
+    pack_id: str = ""
+    active: bool = True
+    available: bool = True
+    production_ready: bool = False

diff --git a/src/processforge_core/process_catalog/service.py b/src/processforge_core/process_catalog/service.py
new file mode 100644
--- /dev/null
+++ b/src/processforge_core/process_catalog/service.py
@@
+from __future__ import annotations
+
+from pathlib import Path
+from typing import Any
+
+from processforge_core.common import load_yaml_document, read_yaml_file, rel, safe_id, yaml_error
+
+from .models import ProcessCatalogContext, ProcessDefinitionRef
+
+
+PROCESS_CATALOG_CLASSIFICATIONS = {
+    "PUBLIC_STABLE",
+    "PUBLIC_EXPERIMENTAL",
+    "INTERNAL_MAINTENANCE",
+    "EXAMPLE_ONLY",
+    "DEPRECATED",
+}
+
+
+def _as_list(value: Any) -> list[Any]:
+    if value is None:
+        return []
+    if isinstance(value, list):
+        return value
+    return [value]
+
+
+def process_catalog_metadata(process: dict[str, Any]) -> dict[str, Any]:
+    catalog = process.get("catalog") if isinstance(process.get("catalog"), dict) else {}
+    status = str(process.get("status") or "draft")
+    classification = str(catalog.get("classification") or "").upper()
+    if classification not in PROCESS_CATALOG_CLASSIFICATIONS:
+        if status == "active":
+            classification = "PUBLIC_STABLE"
+        elif status == "experimental":
+            classification = "PUBLIC_EXPERIMENTAL"
+        elif status == "internal":
+            classification = "INTERNAL_MAINTENANCE"
+        elif status == "deprecated":
+            classification = "DEPRECATED"
+        else:
+            classification = "PUBLIC_EXPERIMENTAL"
+    public_surface = catalog.get("public_surface", process.get("public_surface", classification != "INTERNAL_MAINTENANCE"))
+    return {"classification": classification, "public_surface": bool(public_surface), "status": status}
+
+
+def process_catalog_role(process: dict[str, Any]) -> str:
+    catalog = process.get("catalog") if isinstance(process.get("catalog"), dict) else {}
+    role = str(catalog.get("role") or "").strip()
+    if role:
+        return safe_id(role, "canonical")
+    meta = process_catalog_metadata(process)
+    if meta["classification"] == "INTERNAL_MAINTENANCE":
+        return "internal"
+    if meta["classification"] == "DEPRECATED":
+        return "legacy_alias"
+    return "canonical"
+
+
+def _process_override_declared(process: dict[str, Any], overridden_process_id: str) -> bool:
+    override = process.get("process_override") if isinstance(process.get("process_override"), dict) else {}
+    return str(override.get("overrides") or "") == overridden_process_id and bool(str(override.get("reason") or "").strip())
+
+
+def _official_pack_manifest_records(context: ProcessCatalogContext) -> list[tuple[Path, dict[str, Any]]]:
+    distribution_root = context.distribution_root.resolve()
+    records: list[tuple[Path, dict[str, Any]]] = []
+    for path in sorted((distribution_root / "packs" / "official").glob("*/package.yaml")):
+        data = load_yaml_document(path)
+        if (
+            isinstance(data, dict)
+            and not yaml_error(data)
+            and data.get("kind") == "processforge.pack"
+            and data.get("origin") == "official"
+            and data.get("id")
+        ):
+            records.append((path, data))
+    return records
+
+
+def _official_process_definition_refs(
+    context: ProcessCatalogContext,
+    *,
+    include_available: bool = False,
+) -> list[ProcessDefinitionRef]:
+    active_ids = set(context.active_official_pack_ids)
+    entries: list[ProcessDefinitionRef] = []
+    for manifest_path, manifest in _official_pack_manifest_records(context):
+        pack_id = str(manifest.get("id") or "")
+        active = pack_id in active_ids
+        if not active and not include_available:
+            continue
+        process_root = manifest_path.parent / "processes"
+        provided = manifest.get("provides") if isinstance(manifest.get("provides"), dict) else {}
+        declared = {str(item) for item in _as_list(provided.get("processes")) if str(item)}
+        for path in sorted(process_root.glob("*.yaml")):
+            data = load_yaml_document(path)
+            if yaml_error(data) or not isinstance(data, dict):
+                continue
+            process_id = str(data.get("id") or path.stem)
+            if declared and process_id not in declared:
+                continue
+            entries.append(
+                ProcessDefinitionRef(
+                    process_id=process_id,
+                    path=path,
+                    process=data,
+                    origin="official",
+                    root=manifest_path.parent,
+                    catalog_role=process_catalog_role(data),
+                    warnings=[],
+                    pack_id=pack_id,
+                    active=active,
+                    available=True,
+                    production_ready=bool(manifest.get("production_ready")),
+                )
+            )
+    return entries
+
+
+def _process_root_candidates(context: ProcessCatalogContext) -> list[tuple[Path, str, bool]]:
+    candidates = [
+        (context.flow_root / "processes" / "user", "user", False),
+        (context.flow_root / "processes" / "custom", "custom", False),
+        (context.project_root / "processes" / "user", "user", False),
+        (context.project_root / "processes" / "custom", "custom", False),
+        (context.distribution_root / "processes" / "user", "user", False),
+        (context.distribution_root / "processes" / "custom", "custom", False),
+        (context.project_root / "processes" / "core", "core", False),
+        (context.distribution_root / "processes" / "core", "core", False),
+        (context.flow_root / "processes", "legacy_flat", True),
+        (context.project_root / "processes", "legacy_flat", True),
+        (context.distribution_root / "processes", "legacy_flat", True),
+    ]
+    seen: set[Path] = set()
+    unique: list[tuple[Path, str, bool]] = []
+    for path, origin, legacy in candidates:
+        resolved = path.resolve()
+        if resolved in seen:
+            continue
+        seen.add(resolved)
+        unique.append((path, origin, legacy))
+    return unique
+
+
+def _process_root_yaml_files(root: Path, *, legacy_flat: bool) -> list[Path]:
+    if not root.is_dir():
+        return []
+    if legacy_flat:
+        return sorted([*root.glob("*.yaml"), *root.glob("*.yml")])
+    return sorted([path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in {".yaml", ".yml"}])
+
+
+def process_catalog_entries(
+    context: ProcessCatalogContext,
+    *,
+    strict: bool = False,
+    include_available_official: bool = False,
+) -> list[ProcessDefinitionRef]:
+    selected: dict[str, ProcessDefinitionRef] = {}
+    order: list[str] = []
+    duplicate_messages: dict[str, list[str]] = {}
+
+    def register(entry: ProcessDefinitionRef) -> None:
+        process_id = entry.process_id
+        if process_id not in selected:
+            selected[process_id] = entry
+            order.append(process_id)
+            return
+        current = selected[process_id]
+        message = (
+            f"duplicate process_id {process_id}: {rel(current.path, context.project_root)} "
+            f"wins over {rel(entry.path, context.project_root)}"
+        )
+        if (
+            current.origin in {"user", "custom"}
+            and entry.origin in {"core", "official"}
+            and not _process_override_declared(current.process, process_id)
+        ):
+            message += f"; user/custom override of {entry.origin} process requires process_override.reason"
+        duplicate_messages.setdefault(process_id, []).append(message)
+        if strict:
+            current.warnings.append("STRICT: " + message)
+
+    official_added = False
+    for root, origin, legacy_flat in _process_root_candidates(context):
+        if origin == "core" and not official_added:
+            for official_entry in _official_process_definition_refs(
+                context,
+                include_available=include_available_official,
+            ):
+                register(official_entry)
+            official_added = True
+        for path in _process_root_yaml_files(root, legacy_flat=legacy_flat):
+            data = load_yaml_document(path)
+            if yaml_error(data) or not isinstance(data, dict):
+                continue
+            process_id = str(data.get("id") or path.stem)
+            warnings: list[str] = []
+            if legacy_flat:
+                warnings.append(
+                    f"Legacy flat process path detected: {rel(path, context.project_root)}. Move built-ins to processes/core/ and user processes to processes/user/."
+                )
+            entry = ProcessDefinitionRef(
+                process_id=process_id,
+                path=path,
+                process=data,
+                origin=origin,
+                root=root,
+                catalog_role=process_catalog_role(data),
+                warnings=warnings,
+            )
+            register(entry)
+    for process_id, messages in duplicate_messages.items():
+        selected[process_id].warnings.extend(messages)
+    return [selected[process_id] for process_id in order]
+
+
+def resolve_process_definition(
+    context: ProcessCatalogContext,
+    process_or_path: str,
+    *,
+    include_available_official: bool = False,
+) -> ProcessDefinitionRef:
+    candidate = Path(process_or_path)
+    if candidate.suffix in {".yaml", ".yml"}:
+        path = candidate if candidate.is_absolute() else context.project_root / candidate
+        if path.is_file():
+            for official_entry in _official_process_definition_refs(context, include_available=True):
+                if official_entry.path.resolve() == path.resolve():
+                    return official_entry
+            data = read_yaml_file(path)
+            process_id = str(data.get("id") or path.stem) if isinstance(data, dict) else path.stem
+            origin = "legacy_flat"
+            root = path.parent
+            parts = path.parts
+            if "processes" in parts:
+                try:
+                    index = parts.index("processes")
+                    if len(parts) > index + 1 and parts[index + 1] in {"core", "user", "custom"}:
+                        origin = parts[index + 1]
+                        root = Path(*parts[: index + 2])
+                except ValueError:
+                    pass
+            return ProcessDefinitionRef(
+                process_id,
+                path,
+                data,
+                origin,
+                root,
+                process_catalog_role(data) if isinstance(data, dict) else "canonical",
+                [],
+            )
+    process_id = safe_id(process_or_path, "process")
+    for entry in process_catalog_entries(
+        context,
+        include_available_official=include_available_official,
+    ):
+        if entry.process_id == process_id:
+            return entry
+    for entry in _official_process_definition_refs(context, include_available=True):
+        if entry.process_id == process_id and not entry.active:
+            raise SystemExit(
+                f"FAIL: process {process_id} is available in official pack {entry.pack_id} "
+                "but is not active in this workplace.\n"
+                "Fix: run "
+                f"python bin/pf.py pack-activate --id {entry.pack_id} --workplace <path> --apply"
+            )
+    raise SystemExit(f"FAIL: process not found: {process_id}")
+
+
+def require_official_process_active(context: ProcessCatalogContext, process_id: str) -> None:
+    normalized = safe_id(process_id, "process")
+    effective = next(
+        (
+            entry
+            for entry in process_catalog_entries(
+                context,
+                include_available_official=True,
+            )
+            if entry.process_id == normalized
+        ),
+        None,
+    )
+    if effective is not None and effective.origin == "official" and not effective.active:
+        raise SystemExit(
+            f"FAIL: process {normalized} is available in official pack {effective.pack_id} "
+            "but is not active in this workplace.\n"
+            "Fix: run "
+            f"python bin/pf.py pack-activate --id {effective.pack_id} --workplace <path> --apply"
+        )
+
+
+def process_definition_exists(context: ProcessCatalogContext, process_id: str) -> bool:
+    try:
+        resolve_process_definition(context, process_id)
+        return True
+    except SystemExit:
+        return False

diff --git a/tools/processforge.py b/tools/processforge.py
--- a/tools/processforge.py
+++ b/tools/processforge.py
@@
 from pathlib import Path
 from typing import Any
 from urllib.parse import urlparse
 from urllib.request import url2pathname, urlopen

+def _bootstrap_repo_src() -> Path:
+    repo_root = Path(__file__).resolve().parents[1]
+    src_root = repo_root / "src"
+    src_value = str(src_root)
+    if src_value not in sys.path:
+        first_entry = Path(sys.path[0] or ".").resolve() if sys.path else None
+        tools_root = (repo_root / "tools").resolve()
+        sys.path.insert(1 if first_entry == tools_root else 0, src_value)
+    return repo_root
+
+
+ROOT = _bootstrap_repo_src()
+
+from processforge_core.process_catalog import (
+    ProcessCatalogContext,
+    ProcessDefinitionRef,
+    process_catalog_entries as catalog_process_catalog_entries,
+    process_catalog_role as catalog_process_catalog_role,
+    process_definition_exists as catalog_process_definition_exists,
+    require_official_process_active as catalog_require_official_process_active,
+    resolve_process_definition as catalog_resolve_process_definition,
+)
+from processforge_core.process_catalog import service as process_catalog_core
 from processforge_subprocess import diagnostic_text, format_command as format_subprocess_command, run_command as run_subprocess_command

-
-ROOT = Path(__file__).resolve().parents[1]
 PROJECT_FLOW_ROOT = ".pf"
 PROCESSFORGE_VERSION = "1.0.2"
@@
-@dataclass
-class ProcessDefinitionRef:
-    process_id: str
-    path: Path
-    process: dict[str, Any]
-    origin: str
-    root: Path
-    catalog_role: str
-    warnings: list[str]
-    pack_id: str = ""
-    active: bool = True
-    available: bool = True
-    production_ready: bool = False
-
-
 def safe_id(value: str, default: str = "project") -> str:
     cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
     return cleaned or default
@@
-def process_catalog_role(process: dict[str, Any]) -> str:
-    catalog = process.get("catalog") if isinstance(process.get("catalog"), dict) else {}
-    role = str(catalog.get("role") or "").strip()
-    if role:
-        return safe_id(role, "canonical")
-    meta = process_catalog_metadata(process)
-    if meta["classification"] == "INTERNAL_MAINTENANCE":
-        return "internal"
-    if meta["classification"] == "DEPRECATED":
-        return "legacy_alias"
-    return "canonical"
+def _process_catalog_context(
+    project_root: Path,
+    *,
+    workplace_manifest: Path | None = None,
+) -> ProcessCatalogContext:
+    resolved_project_root = project_root.expanduser().resolve()
+    effective_workplace_manifest = workplace_manifest
+    if effective_workplace_manifest is None:
+        effective_workplace_manifest = resolve_project_workplace_manifest(resolved_project_root)
+    return ProcessCatalogContext(
+        project_root=resolved_project_root,
+        flow_root=locate_flow_root(resolved_project_root),
+        distribution_root=ROOT.resolve(),
+        active_official_pack_ids=frozenset(active_process_pack_ids(effective_workplace_manifest)),
+    )
+
+
+def process_catalog_role(process: dict[str, Any]) -> str:
+    return catalog_process_catalog_role(process)
@@
 def official_process_definition_refs(
     project_root: Path,
     *,
     include_available: bool = False,
     workplace_manifest: Path | None = None,
 ) -> list[ProcessDefinitionRef]:
-    if workplace_manifest is None:
-        workplace_manifest = resolve_project_workplace_manifest(project_root)
-    active_ids = active_process_pack_ids(workplace_manifest)
-    entries: list[ProcessDefinitionRef] = []
-    for manifest_path, manifest in official_pack_manifest_records():
-        pack_id = str(manifest.get("id") or "")
-        active = pack_id in active_ids
-        if not active and not include_available:
-            continue
-        process_root = manifest_path.parent / "processes"
-        provided = manifest.get("provides") if isinstance(manifest.get("provides"), dict) else {}
-        declared = {str(item) for item in as_list(provided.get("processes")) if str(item)}
-        for path in sorted(process_root.glob("*.yaml")):
-            data = load_yaml_document(path)
-            if yaml_error(data) or not isinstance(data, dict):
-                continue
-            process_id = str(data.get("id") or path.stem)
-            if declared and process_id not in declared:
-                continue
-            entries.append(
-                ProcessDefinitionRef(
-                    process_id=process_id,
-                    path=path,
-                    process=data,
-                    origin="official",
-                    root=manifest_path.parent,
-                    catalog_role=process_catalog_role(data),
-                    warnings=[],
-                    pack_id=pack_id,
-                    active=active,
-                    available=True,
-                    production_ready=bool(manifest.get("production_ready")),
-                )
-            )
-    return entries
+    context = _process_catalog_context(project_root, workplace_manifest=workplace_manifest)
+    return process_catalog_core._official_process_definition_refs(
+        context,
+        include_available=include_available,
+    )
@@
 def process_root_candidates(project_root: Path) -> list[tuple[Path, str, bool]]:
-    flow_root = locate_flow_root(project_root)
-    candidates = [
-        (flow_root / "processes" / "user", "user", False),
-        (flow_root / "processes" / "custom", "custom", False),
-        (project_root / "processes" / "user", "user", False),
-        (project_root / "processes" / "custom", "custom", False),
-        (ROOT / "processes" / "user", "user", False),
-        (ROOT / "processes" / "custom", "custom", False),
-        (project_root / "processes" / "core", "core", False),
-        (ROOT / "processes" / "core", "core", False),
-        (flow_root / "processes", "legacy_flat", True),
-        (project_root / "processes", "legacy_flat", True),
-        (ROOT / "processes", "legacy_flat", True),
-    ]
-    seen: set[Path] = set()
-    unique: list[tuple[Path, str, bool]] = []
-    for path, origin, legacy in candidates:
-        resolved = path.resolve()
-        key = resolved
-        if key in seen:
-            continue
-        seen.add(key)
-        unique.append((path, origin, legacy))
-    return unique
+    return process_catalog_core._process_root_candidates(_process_catalog_context(project_root))
@@
 def process_root_yaml_files(root: Path, *, legacy_flat: bool) -> list[Path]:
-    if not root.is_dir():
-        return []
-    if legacy_flat:
-        return sorted([*root.glob("*.yaml"), *root.glob("*.yml")])
-    return sorted([path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in {".yaml", ".yml"}])
+    return process_catalog_core._process_root_yaml_files(root, legacy_flat=legacy_flat)
@@
 def process_catalog_entries(
     project_root: Path,
     *,
     strict: bool = False,
     include_available_official: bool = False,
     workplace_manifest: Path | None = None,
 ) -> list[ProcessDefinitionRef]:
-    selected: dict[str, ProcessDefinitionRef] = {}
-    order: list[str] = []
-    duplicate_messages: dict[str, list[str]] = {}
-
-    def register(entry: ProcessDefinitionRef) -> None:
-        process_id = entry.process_id
-        if process_id not in selected:
-            selected[process_id] = entry
-            order.append(process_id)
-            return
-        current = selected[process_id]
-        message = (
-            f"duplicate process_id {process_id}: {rel(current.path, project_root)} "
-            f"wins over {rel(entry.path, project_root)}"
-        )
-        if (
-            current.origin in {"user", "custom"}
-            and entry.origin in {"core", "official"}
-            and not process_override_declared(current.process, process_id)
-        ):
-            message += f"; user/custom override of {entry.origin} process requires process_override.reason"
-        duplicate_messages.setdefault(process_id, []).append(message)
-        if strict:
-            current.warnings.append("STRICT: " + message)
-
-    official_added = False
-    for root, origin, legacy_flat in process_root_candidates(project_root):
-        if origin == "core" and not official_added:
-            for official_entry in official_process_definition_refs(
-                project_root,
-                include_available=include_available_official,
-                workplace_manifest=workplace_manifest,
-            ):
-                register(official_entry)
-            official_added = True
-        for path in process_root_yaml_files(root, legacy_flat=legacy_flat):
-            data = load_yaml_document(path)
-            if yaml_error(data) or not isinstance(data, dict):
-                continue
-            process_id = str(data.get("id") or path.stem)
-            warnings: list[str] = []
-            if legacy_flat:
-                warnings.append(
-                    f"Legacy flat process path detected: {rel(path, project_root)}. Move built-ins to processes/core/ and user processes to processes/user/."
-                )
-            entry = ProcessDefinitionRef(
-                process_id=process_id,
-                path=path,
-                process=data,
-                origin=origin,
-                root=root,
-                catalog_role=process_catalog_role(data),
-                warnings=warnings,
-            )
-            register(entry)
-    for process_id, messages in duplicate_messages.items():
-        selected[process_id].warnings.extend(messages)
-    return [selected[process_id] for process_id in order]
+    context = _process_catalog_context(project_root, workplace_manifest=workplace_manifest)
+    return catalog_process_catalog_entries(
+        context,
+        strict=strict,
+        include_available_official=include_available_official,
+    )
@@
 def resolve_process_definition(
     project_root: Path,
     process_or_path: str,
     *,
     include_available_official: bool = False,
     workplace_manifest: Path | None = None,
 ) -> ProcessDefinitionRef:
-    candidate = Path(process_or_path)
-    if candidate.suffix in {".yaml", ".yml"}:
-        path = candidate if candidate.is_absolute() else project_root / candidate
-        if path.is_file():
-            for official_entry in official_process_definition_refs(
-                project_root,
-                include_available=True,
-                workplace_manifest=workplace_manifest,
-            ):
-                if official_entry.path.resolve() == path.resolve():
-                    return official_entry
-            data = read_yaml_file(path)
-            process_id = str(data.get("id") or path.stem) if isinstance(data, dict) else path.stem
-            origin = "legacy_flat"
-            root = path.parent
-            parts = path.parts
-            if "processes" in parts:
-                try:
-                    index = parts.index("processes")
-                    if len(parts) > index + 1 and parts[index + 1] in {"core", "user", "custom"}:
-                        origin = parts[index + 1]
-                        root = Path(*parts[: index + 2])
-                except ValueError:
-                    pass
-            return ProcessDefinitionRef(process_id, path, data, origin, root, process_catalog_role(data) if isinstance(data, dict) else "canonical", [])
-    process_id = safe_id(process_or_path, "process")
-    for entry in process_catalog_entries(
-        project_root,
-        include_available_official=include_available_official,
-        workplace_manifest=workplace_manifest,
-    ):
-        if entry.process_id == process_id:
-            return entry
-    for entry in official_process_definition_refs(
-        project_root,
-        include_available=True,
-        workplace_manifest=workplace_manifest,
-    ):
-        if entry.process_id == process_id and not entry.active:
-            raise SystemExit(
-                f"FAIL: process {process_id} is available in official pack {entry.pack_id} "
-                "but is not active in this workplace.\n"
-                "Fix: run "
-                f"python bin/pf.py pack-activate --id {entry.pack_id} --workplace <path> --apply"
-            )
-    raise SystemExit(f"FAIL: process not found: {process_id}")
+    context = _process_catalog_context(project_root, workplace_manifest=workplace_manifest)
+    return catalog_resolve_process_definition(
+        context,
+        process_or_path,
+        include_available_official=include_available_official,
+    )
@@
 def require_official_process_active(project_root: Path, process_id: str) -> None:
-    normalized = safe_id(process_id, "process")
-    effective = next(
-        (
-            entry
-            for entry in process_catalog_entries(
-                project_root,
-                include_available_official=True,
-            )
-            if entry.process_id == normalized
-        ),
-        None,
-    )
-    if effective is not None and effective.origin == "official" and not effective.active:
-        raise SystemExit(
-            f"FAIL: process {normalized} is available in official pack {effective.pack_id} "
-            "but is not active in this workplace.\n"
-            "Fix: run "
-            f"python bin/pf.py pack-activate --id {effective.pack_id} --workplace <path> --apply"
-        )
+    catalog_require_official_process_active(_process_catalog_context(project_root), process_id)
@@
 def process_definition_exists(project_root: Path, process_id: str) -> bool:
-    try:
-        resolve_process_definition(project_root, process_id)
-        return True
-    except SystemExit:
-        return False
+    return catalog_process_definition_exists(_process_catalog_context(project_root), process_id)

diff --git a/tools/pf_runtime/host.py b/tools/pf_runtime/host.py
--- a/tools/pf_runtime/host.py
+++ b/tools/pf_runtime/host.py
@@
 def resolved_process(project_root: Path, process_id: str, core: Any) -> dict[str, Any] | None:
     """Resolve a process once, then invalidate only when its declaration changes."""
-    key = (str(project_root.resolve()), process_id)
+    resolved_project_root = project_root.resolve()
+    key = (str(resolved_project_root), process_id)
     cached = PROCESS_DEFINITION_CACHE.get(key)
     if cached is not None:
         path, modified_ns, process = cached
         try:
             if path.is_file() and path.stat().st_mtime_ns == modified_ns:
                 return process
         except OSError:
             pass
     try:
-        definition = core.resolve_process_definition(project_root, process_id)
+        from processforge_core.process_catalog import (
+            ProcessCatalogContext,
+            resolve_process_definition as resolve_process_definition_core,
+        )
+
+        workplace_manifest = core.resolve_project_workplace_manifest(resolved_project_root)
+        context = ProcessCatalogContext(
+            project_root=resolved_project_root,
+            flow_root=core.locate_flow_root(resolved_project_root),
+            distribution_root=core.ROOT.resolve(),
+            active_official_pack_ids=frozenset(core.active_process_pack_ids(workplace_manifest)),
+        )
+        definition = resolve_process_definition_core(context, process_id)
     except SystemExit:
         return None
     try:
         modified_ns = definition.path.stat().st_mtime_ns
     except OSError:
```

## Механика исправления

- `tools/processforge.py` сам добавляет `<repo>/src` в `sys.path` до первого импорта `processforge_core...`.
- Если скрипт запущен напрямую как `python tools/processforge.py`, `tools/` уже находится в `sys.path[0]`. Вставка `src` в позицию `1` сохраняет порядок `tools -> src`, то есть не ломает текущую модель прямого скриптового запуска и ближе всего к runtime-bootstrap порядку.
- Новый core-срез не импортирует `processforge_core.bootstrap` и не импортирует legacy-модуль `processforge`, поэтому цикла `tools/processforge.py -> processforge_core -> bootstrap -> tools/processforge.py` не появляется.
- Владелец `ProcessDefinitionRef` теперь один: `src/processforge_core/process_catalog/models.py`. Legacy CLI только реиспользует этот же объект класса, поэтому не возникает drift по модульной идентичности.
- В `tools/pf_runtime/host.py` импорт нового core seam сделан лениво внутри `resolved_process()`. Это удерживает изменение ровно в одном seam и не превращает весь `host` в модуль с обязательной top-level зависимостью от `src/processforge_core`.

## Фокусная проверка

```powershell
python tools/processforge.py --help

python -c "import sys; sys.path.insert(0, 'tools'); import processforge as legacy; import processforge_core.process_catalog as cat; assert legacy.ProcessDefinitionRef is cat.ProcessDefinitionRef; print('ok')"

python -c "import sys; sys.path.insert(0, 'src'); from processforge_core.bootstrap import bootstrap_runtime; rt = bootstrap_runtime('src/processforge_core/bootstrap.py'); import processforge_core.process_catalog as cat; assert rt.core.ProcessDefinitionRef is cat.ProcessDefinitionRef; print('ok')"
```

После этого имеет смысл прогнать тот же smoke-набор из исходного дизайна, особенно:

- `smoke_process_resolver_multiple_roots`
- `smoke_process_root_collision_policy`
- `smoke_builtin_process_catalog`
- `smoke_builtin_process_pack_completeness`
- `smoke_runtime_host_poc`
- `smoke_long_lived_runtime`

## Итог

Исправление не расширяет Phase C beyond accepted boundary. Оно только убирает ошибочное внешнее предположение про готовый CLI import-path, делает прямой запуск `tools/processforge.py` самодостаточным для импорта `src/processforge_core`, сохраняет текущие catalog semantics и не создаёт ни bootstrap cycle, ни второго владельца `ProcessDefinitionRef`.