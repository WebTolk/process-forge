from __future__ import annotations

from pathlib import Path
from typing import Any

from processforge_core.common import load_yaml_document, read_yaml_file, rel, safe_id, yaml_error

from .models import ProcessCatalogContext, ProcessDefinitionRef


PROCESS_CATALOG_CLASSIFICATIONS = {
    "PUBLIC_STABLE",
    "PUBLIC_EXPERIMENTAL",
    "INTERNAL_MAINTENANCE",
    "EXAMPLE_ONLY",
    "DEPRECATED",
}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def process_catalog_metadata(process: dict[str, Any]) -> dict[str, Any]:
    catalog = process.get("catalog") if isinstance(process.get("catalog"), dict) else {}
    status = str(process.get("status") or "draft")
    classification = str(catalog.get("classification") or "").upper()
    if classification not in PROCESS_CATALOG_CLASSIFICATIONS:
        if status == "active":
            classification = "PUBLIC_STABLE"
        elif status == "experimental":
            classification = "PUBLIC_EXPERIMENTAL"
        elif status == "internal":
            classification = "INTERNAL_MAINTENANCE"
        elif status == "deprecated":
            classification = "DEPRECATED"
        else:
            classification = "PUBLIC_EXPERIMENTAL"
    public_surface = catalog.get("public_surface", process.get("public_surface", classification != "INTERNAL_MAINTENANCE"))
    return {"classification": classification, "public_surface": bool(public_surface), "status": status}


def process_catalog_role(process: dict[str, Any]) -> str:
    catalog = process.get("catalog") if isinstance(process.get("catalog"), dict) else {}
    role = str(catalog.get("role") or "").strip()
    if role:
        return safe_id(role, "canonical")
    meta = process_catalog_metadata(process)
    if meta["classification"] == "INTERNAL_MAINTENANCE":
        return "internal"
    if meta["classification"] == "DEPRECATED":
        return "legacy_alias"
    return "canonical"


def _process_override_declared(process: dict[str, Any], overridden_process_id: str) -> bool:
    override = process.get("process_override") if isinstance(process.get("process_override"), dict) else {}
    return str(override.get("overrides") or "") == overridden_process_id and bool(str(override.get("reason") or "").strip())


def _official_pack_manifest_records(context: ProcessCatalogContext) -> list[tuple[Path, dict[str, Any]]]:
    distribution_root = context.distribution_root.resolve()
    records: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted((distribution_root / "packs" / "official").glob("*/package.yaml")):
        data = load_yaml_document(path)
        if (
            isinstance(data, dict)
            and not yaml_error(data)
            and data.get("kind") == "processforge.pack"
            and data.get("origin") == "official"
            and data.get("id")
        ):
            records.append((path, data))
    return records


def _official_process_definition_refs(
    context: ProcessCatalogContext,
    *,
    include_available: bool = False,
) -> list[ProcessDefinitionRef]:
    active_ids = set(context.active_official_pack_ids)
    entries: list[ProcessDefinitionRef] = []
    for manifest_path, manifest in _official_pack_manifest_records(context):
        pack_id = str(manifest.get("id") or "")
        active = pack_id in active_ids
        if not active and not include_available:
            continue
        process_root = manifest_path.parent / "processes"
        provided = manifest.get("provides") if isinstance(manifest.get("provides"), dict) else {}
        declared = {str(item) for item in _as_list(provided.get("processes")) if str(item)}
        for path in sorted(process_root.glob("*.yaml")):
            data = load_yaml_document(path)
            if yaml_error(data) or not isinstance(data, dict):
                continue
            process_id = str(data.get("id") or path.stem)
            if declared and process_id not in declared:
                continue
            entries.append(
                ProcessDefinitionRef(
                    process_id=process_id,
                    path=path,
                    process=data,
                    origin="official",
                    root=manifest_path.parent,
                    catalog_role=process_catalog_role(data),
                    warnings=[],
                    pack_id=pack_id,
                    active=active,
                    available=True,
                    production_ready=bool(manifest.get("production_ready")),
                )
            )
    return entries


def official_process_definition_refs(
    context: ProcessCatalogContext,
    *,
    include_available: bool = False,
) -> list[ProcessDefinitionRef]:
    return _official_process_definition_refs(
        context,
        include_available=include_available,
    )


def _process_root_candidates(context: ProcessCatalogContext) -> list[tuple[Path, str, bool]]:
    candidates = [
        (context.flow_root / "processes" / "user", "user", False),
        (context.flow_root / "processes" / "custom", "custom", False),
        (context.project_root / "processes" / "user", "user", False),
        (context.project_root / "processes" / "custom", "custom", False),
        (context.distribution_root / "processes" / "user", "user", False),
        (context.distribution_root / "processes" / "custom", "custom", False),
        (context.project_root / "processes" / "core", "core", False),
        (context.distribution_root / "processes" / "core", "core", False),
        (context.flow_root / "processes", "legacy_flat", True),
        (context.project_root / "processes", "legacy_flat", True),
        (context.distribution_root / "processes", "legacy_flat", True),
    ]
    seen: set[Path] = set()
    unique: list[tuple[Path, str, bool]] = []
    for path, origin, legacy in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append((path, origin, legacy))
    return unique


def process_root_candidates(
    context: ProcessCatalogContext,
) -> list[tuple[Path, str, bool]]:
    return _process_root_candidates(context)


def _process_root_yaml_files(root: Path, *, legacy_flat: bool) -> list[Path]:
    if not root.is_dir():
        return []
    if legacy_flat:
        return sorted([*root.glob("*.yaml"), *root.glob("*.yml")])
    return sorted([path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in {".yaml", ".yml"}])


def process_root_yaml_files(root: Path, *, legacy_flat: bool) -> list[Path]:
    return _process_root_yaml_files(root, legacy_flat=legacy_flat)


def process_catalog_entries(
    context: ProcessCatalogContext,
    *,
    strict: bool = False,
    include_available_official: bool = False,
) -> list[ProcessDefinitionRef]:
    selected: dict[str, ProcessDefinitionRef] = {}
    order: list[str] = []
    duplicate_messages: dict[str, list[str]] = {}

    def register(entry: ProcessDefinitionRef) -> None:
        process_id = entry.process_id
        if process_id not in selected:
            selected[process_id] = entry
            order.append(process_id)
            return
        current = selected[process_id]
        message = (
            f"duplicate process_id {process_id}: {rel(current.path, context.project_root)} "
            f"wins over {rel(entry.path, context.project_root)}"
        )
        if (
            current.origin in {"user", "custom"}
            and entry.origin in {"core", "official"}
            and not _process_override_declared(current.process, process_id)
        ):
            message += f"; user/custom override of {entry.origin} process requires process_override.reason"
        duplicate_messages.setdefault(process_id, []).append(message)
        if strict:
            current.warnings.append("STRICT: " + message)

    official_added = False
    for root, origin, legacy_flat in _process_root_candidates(context):
        if origin == "core" and not official_added:
            for official_entry in _official_process_definition_refs(
                context,
                include_available=include_available_official,
            ):
                register(official_entry)
            official_added = True
        for path in _process_root_yaml_files(root, legacy_flat=legacy_flat):
            data = load_yaml_document(path)
            if yaml_error(data) or not isinstance(data, dict):
                continue
            process_id = str(data.get("id") or path.stem)
            warnings: list[str] = []
            if legacy_flat:
                warnings.append(
                    f"Legacy flat process path detected: {rel(path, context.project_root)}. Move built-ins to processes/core/ and user processes to processes/user/."
                )
            entry = ProcessDefinitionRef(
                process_id=process_id,
                path=path,
                process=data,
                origin=origin,
                root=root,
                catalog_role=process_catalog_role(data),
                warnings=warnings,
            )
            register(entry)
    for process_id, messages in duplicate_messages.items():
        selected[process_id].warnings.extend(messages)
    return [selected[process_id] for process_id in order]


def resolve_process_definition(
    context: ProcessCatalogContext,
    process_or_path: str,
    *,
    include_available_official: bool = False,
) -> ProcessDefinitionRef:
    candidate = Path(process_or_path)
    if candidate.suffix in {".yaml", ".yml"}:
        path = candidate if candidate.is_absolute() else context.project_root / candidate
        if path.is_file():
            for official_entry in _official_process_definition_refs(context, include_available=True):
                if official_entry.path.resolve() == path.resolve():
                    return official_entry
            data = read_yaml_file(path)
            process_id = str(data.get("id") or path.stem) if isinstance(data, dict) else path.stem
            origin = "legacy_flat"
            root = path.parent
            parts = path.parts
            if "processes" in parts:
                try:
                    index = parts.index("processes")
                    if len(parts) > index + 1 and parts[index + 1] in {"core", "user", "custom"}:
                        origin = parts[index + 1]
                        root = Path(*parts[: index + 2])
                except ValueError:
                    pass
            return ProcessDefinitionRef(
                process_id,
                path,
                data,
                origin,
                root,
                process_catalog_role(data) if isinstance(data, dict) else "canonical",
                [],
            )
    process_id = safe_id(process_or_path, "process")
    for entry in process_catalog_entries(
        context,
        include_available_official=include_available_official,
    ):
        if entry.process_id == process_id:
            return entry
    for entry in _official_process_definition_refs(context, include_available=True):
        if entry.process_id == process_id and not entry.active:
            raise SystemExit(
                f"FAIL: process {process_id} is available in official pack {entry.pack_id} "
                "but is not active in this workplace.\n"
                "Fix: run "
                f"python bin/pf.py pack-activate --id {entry.pack_id} --workplace <path> --apply"
            )
    raise SystemExit(f"FAIL: process not found: {process_id}")


def require_official_process_active(context: ProcessCatalogContext, process_id: str) -> None:
    normalized = safe_id(process_id, "process")
    effective = next(
        (
            entry
            for entry in process_catalog_entries(
                context,
                include_available_official=True,
            )
            if entry.process_id == normalized
        ),
        None,
    )
    if effective is not None and effective.origin == "official" and not effective.active:
        raise SystemExit(
            f"FAIL: process {normalized} is available in official pack {effective.pack_id} "
            "but is not active in this workplace.\n"
            "Fix: run "
            f"python bin/pf.py pack-activate --id {effective.pack_id} --workplace <path> --apply"
        )


def process_definition_exists(context: ProcessCatalogContext, process_id: str) -> bool:
    try:
        resolve_process_definition(context, process_id)
        return True
    except SystemExit:
        return False
