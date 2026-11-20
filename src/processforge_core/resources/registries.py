"""Concrete live workplace registry reads and their root-independent path rules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..work.context_documents import ContextContractInputs, PATH_CONSTANT_PATTERN

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


class WorkplaceRegistryReader:
    """Read registries with concrete inputs and no captured project or workplace."""

    def __init__(self, inputs: ContextContractInputs | None = None) -> None:
        self.inputs = inputs if inputs is not None else ContextContractInputs()

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

    def path_resolution_to_path(self, resolution: dict[str, Any]) -> Path:
        return Path(str(resolution.get('resolved') or resolution.get('expanded') or resolution.get('original') or ''))

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

    def normalize_workplace_manifest(self, path: Path | None) -> Path | None:
        if path is None:
            return None
        candidate = path.expanduser().resolve()
        if candidate.is_dir():
            candidate = candidate / 'workplace.yaml'
        return candidate
