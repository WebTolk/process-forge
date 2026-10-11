"""Existing snapshot selection and concrete live resource path resolution."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

from ..common.paths import rel
from ..project.metadata import ProjectMetadataReader
from ..work.context_documents import ContextContractInputs, PATH_CONSTANT_PATTERN

__all__ = ()

DEFAULT_PATH_CONSTANTS = {
    "PF_WORKPLACE": ".",
    "PF_DISTRIBUTION": "distributions/processforge",
    "PF_KNOWLEDGE": "knowledge",
    "PF_TEMPLATES": "reusable-templates",
    "PF_TOOLS": "tools",
    "PF_MCP": "mcp",
    "PF_PLATFORM_CONTRACTS": "platform-contracts",
    "PF_SPECIALIZATIONS": "specializations",
    "PF_PROCESS_TEMPLATES": "process-templates",
    "PF_RUNTIME": "runtime",
    "PF_CACHE": "cache",
}

RESOURCE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$")

WINDOWS_RESERVED_DEVICE_BASENAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *{f"com{index}" for index in range(1, 10)},
    *{f"lpt{index}" for index in range(1, 10)},
}

@dataclass
class _PackageRootResolution:
    root_id: str
    original_path: str
    resolved_path: Path
    status: str
    warnings: list[str]
    fallback: bool = False
    entry: dict[str, Any] | None = None

@dataclass(frozen=True)
class WorkspacePathReferenceReader:
    """Own the existing package/registry read graph, with concrete Core inputs."""
    project_root: Path
    workplace_root: Path | None
    workplace_manifest: Path | None = field(default=None, kw_only=True)
    inputs: ContextContractInputs = field(default_factory=ContextContractInputs, kw_only=True, repr=False, compare=False)

    def validate_resource_id(self, raw: str, resource_kind: str='resource') -> str:
        value = str(raw)
        invalid_reason = ''
        if not value:
            invalid_reason = 'must not be empty'
        elif value != value.strip() or any((ord(char) < 32 or ord(char) == 127 for char in value)):
            invalid_reason = 'must not contain whitespace or control characters'
        elif '%' in value:
            invalid_reason = 'must not contain percent-encoded path characters'
        elif '/' in value or '\\' in value:
            invalid_reason = 'must not contain path separators'
        elif ':' in value or re.match('^[a-zA-Z]:', value):
            invalid_reason = 'must not contain drive, URI, or alternate-stream syntax'
        elif value.endswith(('.', ' ')):
            invalid_reason = 'must not end with a Windows-trimmed dot or space'
        elif any((segment in {'', '.', '..'} for segment in value.split('.'))):
            invalid_reason = 'must not contain empty or relative dot segments'
        elif value.split('.', 1)[0] in WINDOWS_RESERVED_DEVICE_BASENAMES:
            invalid_reason = 'must not use a Windows reserved device basename'
        elif not RESOURCE_ID_PATTERN.fullmatch(value):
            invalid_reason = 'must match ^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$'
        if invalid_reason:
            raise SystemExit(f'FAIL: invalid {resource_kind} id {value!r}: {invalid_reason}')
        return value

    def contained_resource_path(self, root: Path, target: Path, resource_kind: str='resource') -> Path:
        try:
            resolved_root = root.expanduser().resolve()
            resolved_target = target.expanduser().resolve()
            resolved_target.relative_to(resolved_root)
        except (OSError, RuntimeError, ValueError) as exc:
            raise SystemExit(f'FAIL: invalid {resource_kind} target cannot be contained under declared root: {target.as_posix()}') from exc
        return resolved_target

    def path_string_is_absolute(self, value: str) -> bool:
        return self.inputs.path_string_is_absolute(value)

    def normalize_path_string(self, value: str) -> str:
        return value.replace('\\', '/')

    def load_workplace_path_constants(self, workplace_manifest: Path | None, workplace_root: Path | None=None) -> dict[str, str]:
        root = workplace_root or (workplace_manifest.parent if workplace_manifest else Path('.').resolve())
        constants = dict(DEFAULT_PATH_CONSTANTS)
        if workplace_manifest and workplace_manifest.is_file():
            data = self.load_yaml_document(workplace_manifest)
            raw_constants = data.get('path_constants') if isinstance(data, dict) else None
            if isinstance(raw_constants, dict):
                for key, value in raw_constants.items():
                    if isinstance(key, str):
                        constants[key] = '' if value is None else str(value)
        constants.setdefault('PF_WORKPLACE', '.')
        constants['_WORKPLACE_ROOT'] = root.as_posix()
        return constants

    def expand_path_constants(self, raw_path: str, constants: dict[str, str]) -> tuple[str, list[str], list[str]]:
        expanded = raw_path
        used: list[str] = []
        errors: list[str] = []
        visiting: list[str] = []

        def expand_const(name: str) -> str:
            if name in visiting:
                errors.append('cyclic path constant reference: ' + ' -> '.join([*visiting, name]))
                return '${' + name + '}'
            if name not in constants:
                errors.append(f'unknown path constant: {name}')
                return '${' + name + '}'
            value = str(constants.get(name, ''))
            if value == '':
                errors.append(f'empty path constant: {name}')
                return ''
            used.append(name)
            visiting.append(name)
            result = PATH_CONSTANT_PATTERN.sub(lambda match: expand_const(match.group(1)), value)
            visiting.pop()
            return result
        for _ in range(20):
            if not PATH_CONSTANT_PATTERN.search(expanded):
                break
            before = expanded
            expanded = PATH_CONSTANT_PATTERN.sub(lambda match: expand_const(match.group(1)), expanded)
            if expanded == before:
                break
        if PATH_CONSTANT_PATTERN.search(expanded):
            errors.append('unresolved path constant reference remains')
        return (expanded, sorted(set(used)), sorted(set(errors)))

    def resolve_path_with_constants(self, raw_path: str | None, base_dir: Path, constants: dict[str, str] | None=None) -> dict[str, Any]:
        original = '' if raw_path is None else str(raw_path)
        constants = constants or self.load_workplace_path_constants(None, base_dir)
        expanded, used_constants, errors = self.expand_path_constants(original, constants)
        expanded = self.normalize_path_string(expanded)
        status = 'resolved'
        if errors:
            status = 'error'
        elif used_constants:
            status = 'resolved_from_constant'
        elif self.path_string_is_absolute(expanded):
            status = 'absolute'
        else:
            status = 'resolved_relative'
        if self.path_string_is_absolute(expanded):
            resolved = expanded
            is_absolute = True
        else:
            resolved = self.normalize_path_string((base_dir / expanded).resolve().as_posix())
            is_absolute = True
        return {'original': original, 'expanded': expanded, 'resolved': resolved, 'is_absolute': is_absolute, 'is_private': is_absolute, 'path_status': status, 'constants': used_constants, 'errors': errors}

    def workplace_path_resolution(self, workplace_root: Path, raw_path: str | None) -> dict[str, Any]:
        manifest = workplace_root / 'workplace.yaml'
        return self.resolve_path_with_constants(raw_path, workplace_root, self.load_workplace_path_constants(manifest, workplace_root))

    def path_resolution_to_path(self, resolution: dict[str, Any]) -> Path:
        return Path(str(resolution.get('resolved') or resolution.get('expanded') or resolution.get('original') or ''))

    def locate_flow_root(self, project_root: Path, *, prefer_pf: bool=True) -> Path:
        return ProjectMetadataReader(project_root, documents=self.inputs.documents).flow_root(prefer_pf=prefer_pf)

    def load_workplace_registry(self, workplace_manifest: Path | None, registry_key: str, default_name: str) -> dict[str, Any]:
        if not workplace_manifest or not workplace_manifest.is_file():
            return {}
        path = self.resolve_registry_path(workplace_manifest, registry_key, default_name)
        return self.load_yaml_document(path)

    def resolve_registry_relative_path(self, base: Path, raw_path: str, workplace_manifest: Path | None=None) -> Path:
        constants = self.load_workplace_path_constants(workplace_manifest, base) if workplace_manifest else self.load_workplace_path_constants(None, base)
        resolution = self.resolve_path_with_constants(raw_path, base, constants)
        return self.path_resolution_to_path(resolution)

    def resolve_registry_path(self, workplace_manifest: Path, registry_key: str, default_name: str) -> Path:
        workplace = self.load_yaml_document(workplace_manifest)
        registries = workplace.get('registries', {}) if isinstance(workplace, dict) and isinstance(workplace.get('registries'), dict) else {}
        raw_path = str(registries.get(registry_key) or f'registries/{default_name}')
        return self.resolve_registry_relative_path(workplace_manifest.parent, raw_path, workplace_manifest)

    def load_yaml_document(self, path: Path) -> dict[str, Any]:
        return self.inputs.load_yaml_document(path)

    def yaml_error(self, data: Any) -> str | None:
        if isinstance(data, dict) and isinstance(data.get('__yaml_error__'), str):
            return str(data['__yaml_error__'])
        return None

    def package_root_entries(self, workplace_root: Path) -> list[dict[str, Any]]:
        registry = self.load_yaml_document(workplace_root / 'registries' / 'package-roots.yaml')
        entries = registry.get('package_roots') if isinstance(registry, dict) else None
        return [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []

    def package_root_resolution_from_entry(self, workplace_root: Path, entry: dict[str, Any]) -> _PackageRootResolution:
        root_id = str(entry.get('id', 'package-root'))
        original = str(entry.get('path', ''))
        resolution = self.workplace_path_resolution(workplace_root, original)
        warnings = [str(item) for item in resolution.get('errors', [])]
        return _PackageRootResolution(root_id=root_id, original_path=original, resolved_path=self.path_resolution_to_path(resolution), status=str(entry.get('status', 'available')), warnings=warnings, fallback=False, entry=entry)

    def resolve_package_root(self, workplace_root: Path, package_root_id: str | None=None, *, mode: str='read') -> _PackageRootResolution:
        entries = self.package_root_entries(workplace_root)
        fallback = _PackageRootResolution(root_id='fallback', original_path='packages', resolved_path=workplace_root / 'packages', status='fallback', warnings=['WARN: registries/package-roots.yaml is missing or empty; using fallback <workplace-root>/packages'], fallback=True, entry=None)
        if not entries:
            return fallback
        if package_root_id:
            for entry in entries:
                if str(entry.get('id')) == package_root_id:
                    selected = self.package_root_resolution_from_entry(workplace_root, entry)
                    break
            else:
                raise SystemExit(f"FAIL: package root '{package_root_id}' not found in registries/package-roots.yaml")
        else:
            available = [entry for entry in entries if str(entry.get('status', 'available')) == 'available']
            default_entries = [entry for entry in available if bool(entry.get('default', False))]
            selected_entry = default_entries[0] if default_entries else available[0] if available else None
            if selected_entry is None:
                existing = [entry for entry in entries if entry.get('path') and self.package_root_resolution_from_entry(workplace_root, entry).resolved_path.exists()]
                selected_entry = existing[0] if existing else entries[0]
            selected = self.package_root_resolution_from_entry(workplace_root, selected_entry)
        if selected.warnings:
            if mode == 'write':
                if not selected.fallback:
                    raise SystemExit('FAIL: package root path cannot be resolved: ' + '; '.join(selected.warnings))
        if not selected.fallback and (not selected.resolved_path.is_dir()):
            selected.warnings.append(f"WARN: package root '{selected.root_id}' path does not exist: {selected.resolved_path.as_posix()}")
        if selected.entry is not None and str(selected.entry.get('writable', True)).lower() == 'false' and (mode == 'write'):
            raise SystemExit(f"FAIL: package root '{selected.root_id}' is not writable")
        if mode == 'write' and (not selected.fallback) and (not selected.resolved_path.is_dir()):
            raise SystemExit(f"FAIL: selected package root '{selected.root_id}' path does not exist: {selected.resolved_path.as_posix()}")
        return selected

    def package_path_candidates(self, root_path: Path, package_id: str) -> list[Path]:
        validated_id = self.validate_resource_id(package_id, 'knowledge package')
        return [self.contained_resource_path(root_path, root_path / validated_id / 'package.yaml', 'knowledge package'), self.contained_resource_path(root_path, root_path / f'{validated_id}.yaml', 'knowledge package')]

    def resolve_package_path(self, workplace_root: Path, package_id: str, package_root_id: str | None=None, *, mode: str='read') -> tuple[_PackageRootResolution, Path]:
        validated_id = self.validate_resource_id(package_id, 'knowledge package')
        root = self.resolve_package_root(workplace_root, package_root_id, mode=mode)
        return (root, self.contained_resource_path(root.resolved_path, root.resolved_path / validated_id / 'package.yaml', 'knowledge package'))

    def find_workplace_package_manifests(self, workplace_root: Path, package_id: str) -> list[tuple[_PackageRootResolution, Path]]:
        manifests: list[tuple[_PackageRootResolution, Path]] = []
        roots = self.package_root_entries(workplace_root)
        if roots:
            root_resolutions = [self.package_root_resolution_from_entry(workplace_root, entry) for entry in roots]
        else:
            root_resolutions = [self.resolve_package_root(workplace_root, None, mode='read')]
        for root in root_resolutions:
            if root.warnings and (not root.fallback):
                continue
            for path in self.package_path_candidates(root.resolved_path, package_id):
                if path.is_file():
                    manifests.append((root, path))
        return manifests

    def load_workplace_package_manifest(self, workplace_root: Path, package_id: str, package_root_id: str | None=None, *, mode: str='read') -> tuple[Path, dict[str, Any], _PackageRootResolution]:
        existing = self.find_workplace_package_manifests(workplace_root, package_id)
        if package_root_id:
            root, default_path = self.resolve_package_path(workplace_root, package_id, package_root_id, mode=mode)
            path = default_path
            for existing_root, existing_path in existing:
                if existing_root.root_id == root.root_id:
                    root, path = (existing_root, existing_path)
                    break
        elif existing:
            if len(existing) > 1:
                roots = ', '.join((f'{root.root_id}:{path.as_posix()}' for root, path in existing))
                root, path = existing[0]
                root.warnings.append(f"WARN: duplicate package id '{package_id}' found across package roots: {roots}")
            else:
                root, path = existing[0]
        else:
            root, path = self.resolve_package_path(workplace_root, package_id, None, mode=mode)
        data = self.load_yaml_document(path)
        error = self.yaml_error(data)
        if error:
            if mode == 'write':
                raise SystemExit(f'FAIL: package manifest YAML invalid: {rel(path, workplace_root)}: {error}')
            return (path, data, root)
        if not data:
            data = {'schema_version': 1, 'id': package_id, 'name': package_id.replace('.', ' ').replace('-', ' ').title(), 'version': '1.0.0', 'kind': 'documentation' if 'docs' in package_id or 'documentation' in package_id else 'platform', 'scope': 'workplace', 'resources': []}
        if 'resources' not in data or not isinstance(data.get('resources'), list):
            data['resources'] = []
        return (path, data, root)

    def workspace_registry_specs(self) -> dict[str, tuple[str, str, str]]:
        return {'knowledge_roots': ('knowledge_roots', 'knowledge-roots.yaml', 'knowledge_roots'), 'template_roots': ('template_roots', 'templates.yaml', 'template_roots'), 'templates': ('templates', 'templates.yaml', 'templates'), 'package_roots': ('package_roots', 'package-roots.yaml', 'package_roots'), 'tools': ('tools', 'tools.yaml', 'tools'), 'mcp': ('mcp', 'mcp.yaml', 'mcp_servers'), 'private_resource_paths': ('private_resource_paths', 'private-resource-paths.yaml', 'private_resource_paths')}

    def workplace_registry_entry(self, workplace_manifest: Path | None, registry: str, ref_id: str) -> dict[str, Any] | None:
        spec = self.workspace_registry_specs().get(registry)
        if not spec or not workplace_manifest:
            return None
        registry_key, default_name, collection_key = spec
        data = self.load_workplace_registry(workplace_manifest, registry_key, default_name)
        entries = data.get(collection_key) if isinstance(data, dict) else None
        if not isinstance(entries, list):
            return None
        for entry in entries:
            if isinstance(entry, dict) and str(entry.get('id') or '') == ref_id:
                return entry
        return None

    def resolve(self, path_ref: dict[str, Any]) -> dict[str, Any]:
        project_root = self.project_root
        manifest_path = self.workplace_manifest
        if manifest_path is None and self.workplace_root is not None:
            manifest_path = self.workplace_root / 'workplace.yaml'
        manifest = self.normalize_workplace_manifest(manifest_path)
        workplace_root = manifest.parent if manifest else None
        package_id = str(path_ref.get('package') or '')
        relative_path = str(path_ref.get('relative_path') or '').strip()
        if package_id:
            bases: list[Path] = []
            if package_id == 'self':
                bases.append(project_root)
            else:
                bases.append(self.locate_flow_root(project_root) / 'packages' / package_id)
                if workplace_root:
                    manifest_path, _manifest, _package_root = self.load_workplace_package_manifest(workplace_root, package_id, mode='read')
                    if manifest_path:
                        bases.append(manifest_path.parent)
            for base in bases:
                resolved_base = base.resolve()
                candidate = (resolved_base / relative_path).resolve() if relative_path else resolved_base
                try:
                    candidate.relative_to(resolved_base)
                except ValueError:
                    return {'status': 'unresolved', 'reason': 'invalid_path_ref: relative_path escapes declared package root'}
                if candidate.exists():
                    return {'status': 'resolved', 'path': str(candidate)}
            return {'status': 'unresolved', 'reason': f'package path not found: {package_id}/{relative_path}'.rstrip('/')}
        registry = str(path_ref.get('registry') or '')
        ref_id = str(path_ref.get('id') or '')
        if registry == 'external_resources':
            return {'status': 'external', 'url': path_ref.get('url') or ''}
        if not registry or not ref_id:
            return {'status': 'unresolved', 'reason': 'path_ref must include package or registry/id'}
        if not manifest or not workplace_root:
            return {'status': 'unresolved', 'reason': 'workplace manifest is not configured'}
        entry = self.workplace_registry_entry(manifest, registry, ref_id)
        if not entry:
            return {'status': 'unresolved', 'reason': f'registry target missing: {registry}/{ref_id}'}
        raw_path = entry.get('path')
        if not raw_path:
            return {'status': 'descriptor', 'entry': {str(key): value for key, value in entry.items() if str(key) != 'path'}}
        root_resolution = self.workplace_path_resolution(workplace_root, str(raw_path))
        if root_resolution.get('errors'):
            return {'status': 'unresolved', 'reason': '; '.join((str(item) for item in root_resolution.get('errors', [])))}
        base = self.path_resolution_to_path(root_resolution).resolve()
        if registry not in {'private_resource_paths', 'knowledge_roots'}:
            try:
                base.relative_to(workplace_root.resolve())
            except ValueError:
                return {'status': 'unresolved', 'reason': 'invalid_path_ref: registry path escapes workplace root'}
        candidate = (base / relative_path).resolve() if relative_path else base
        try:
            candidate.relative_to(base)
        except ValueError:
            return {'status': 'unresolved', 'reason': 'invalid_path_ref: relative_path escapes declared registry root'}
        return {'status': 'resolved' if candidate.exists() else 'missing', 'path': str(candidate)}

    def normalize_workplace_manifest(self, path: Path | None) -> Path | None:
        if path is None:
            return None
        candidate = path.expanduser().resolve()
        if candidate.is_dir():
            candidate = candidate / 'workplace.yaml'
        return candidate


def snapshot_with_resolved_search_roots(project_root: Path, snapshot: dict[str, Any], workplace_root: Path) -> dict[str, Any]:
    runtime_snapshot = copy.deepcopy(snapshot)
    resources = runtime_snapshot.get("local_search_resources") if isinstance(runtime_snapshot.get("local_search_resources"), list) else []
    for resource in resources:
        if not isinstance(resource, dict) or not isinstance(resource.get("path_ref"), dict):
            continue
        resolution = resolve_garage_path_ref(project_root, resource["path_ref"], workplace_root)
        if resolution.get("status") == "resolved" and resolution.get("path"):
            resource["content_roots"] = [str(resolution["path"])]
    return runtime_snapshot


def resolve_garage_path_ref(project_root: Path, path_ref: dict[str, Any], workplace_root: Path) -> dict[str, Any]:
    reader = WorkspacePathReferenceReader(project_root, workplace_root)
    resolution = reader.resolve(path_ref)
    if resolution.get("status") == "resolved":
        return resolution
    package_id = str(path_ref.get("package") or "")
    relative_path = str(path_ref.get("relative_path") or "").strip()
    if not package_id.startswith("project."):
        return resolution
    base = ProjectMetadataReader(project_root, documents=reader.inputs.documents).flow_root()
    candidate = (base / relative_path).resolve() if relative_path else base.resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError:
        return {"status": "unresolved", "reason": "invalid_path_ref: relative_path escapes project flow root"}
    return {"status": "resolved" if candidate.exists() else "missing", "path": str(candidate)}

def selected_resource(snapshot: dict[str, Any], resource_id: str) -> dict[str, Any]:
    candidates: list[Any] = []
    resolved = snapshot.get("resolved") if isinstance(snapshot.get("resolved"), dict) else {}
    for key in ("knowledge_resources",):
        if isinstance(resolved.get(key), list):
            candidates.extend(resolved[key])
    if isinstance(snapshot.get("local_search_resources"), list):
        candidates.extend(snapshot["local_search_resources"])
    for item in candidates:
        if not isinstance(item, dict):
            continue
        ids = {str(item.get("id") or ""), str(item.get("resource_id") or ""), str(item.get("instance_id") or "")}
        if resource_id in ids:
            return item
    return {}


def resource_selection_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    selection = snapshot.get("resource_selection") if isinstance(snapshot.get("resource_selection"), dict) else {}
    resolved = snapshot.get("resolved") if isinstance(snapshot.get("resolved"), dict) else {}
    selected = resolved.get("knowledge_resources") if isinstance(resolved.get("knowledge_resources"), list) else []
    preferred = [
        {
            "id": str(item.get("id") or ""),
            "kind": str(item.get("kind") or ""),
            "version": str(item.get("resolved_version") or item.get("resolved_generation") or ""),
            "reason": str((item.get("selection") or {}).get("reason") or ""),
        }
        for item in selected
        if isinstance(item, dict)
    ]
    return {
        "mode": str(selection.get("mode") or "snapshot"),
        "available_count": int(selection.get("available_count") or len(resolved.get("available_knowledge_resources") or [])),
        "selected_count": int(selection.get("selected_count") or len(preferred)),
        "target_versions": selection.get("target_versions") if isinstance(selection.get("target_versions"), list) else [],
        "preferred": preferred,
    }


def add_private_navigation(payload: dict[str, Any], runtime_snapshot: dict[str, Any]) -> None:
    resources = runtime_snapshot.get("local_search_resources") if isinstance(runtime_snapshot.get("local_search_resources"), list) else []
    by_id = {str(item.get("id") or item.get("resource_id") or ""): item for item in resources if isinstance(item, dict)}
    for match in payload.get("results", []):
        if not isinstance(match, dict):
            continue
        resource = by_id.get(str(match.get("resource_id") or ""))
        roots = resource.get("content_roots") if isinstance(resource, dict) and isinstance(resource.get("content_roots"), list) else []
        for raw_root in roots:
            root = Path(str(raw_root)).resolve()
            candidate = (root / str(match.get("canonical_path") or "")).resolve() if root.is_dir() else root
            try:
                candidate.relative_to(root if root.is_dir() else candidate)
            except ValueError:
                continue
            if candidate.is_file():
                match["local_path"] = str(candidate)
                match["navigation"] = "private_runtime_authorized"
                break
