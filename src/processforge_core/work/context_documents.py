from __future__ import annotations

from dataclasses import dataclass, field
import fnmatch
import json
import os
from pathlib import Path
import re
from typing import Any

from ..common.ids import safe_id
from ..common.paths import rel
from ..common.values import as_list
from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader
from ..project.metadata import PROJECT_FLOW_ROOT, ProjectMetadataReader

WORKSPACE_ACCESS_KEYS = ("knowledge_resources", "templates", "tools", "mcp")
PATH_CONSTANT_PATTERN = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")
ASSIGNMENT_ID_PATTERN = re.compile(r"^(?:[a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])$")


@dataclass(frozen=True)
class ContextContractInputs:
    """Concrete document and field inputs to the existing context read rules."""

    documents: YamlDocumentReader = field(default_factory=lambda: YamlDocumentReader(_parse_simple_yaml))

    def load_yaml_document(self, path: Path) -> dict[str, Any]:
        return self.documents.load(path)

    def rel(self, path: Path, root: Path) -> str:
        return rel(path, root)

    def assignment_path(self, project_root: Path, assignment_id: str) -> Path:
        identifier = str(assignment_id or "")
        if not ASSIGNMENT_ID_PATTERN.fullmatch(identifier):
            raise ValueError(f"unsafe assignment id: {identifier!r}")
        return self.locate_flow_root(project_root) / "assignments" / f"{identifier}.yaml"

    def _list(self, value: Any) -> list[Any]:
        return value if isinstance(value, list) else []

    def normalize_assignment_path(self, value: Any) -> str:
        text = str(value or '').strip().replace('\\', '/')
        while text.startswith('./'):
            text = text[2:]
        text = re.sub('/+', '/', text)
        return text.rstrip('/') if text not in {'', '/'} else text

    def assignment_scope_items(self, value: Any) -> list[str]:
        items: list[str] = []
        seen: set[str] = set()
        for item in self._list(value):
            raw: Any = item
            if isinstance(item, dict):
                raw = item.get('path') or item.get('glob') or item.get('pattern') or item.get('file')
            text = self.normalize_assignment_path(raw)
            if text and text not in seen:
                items.append(text)
                seen.add(text)
        return items

    def assignment_path_key(self, value: Any) -> str:
        text = self.normalize_assignment_path(value)
        return text.lower() if os.name == "nt" else text

    def assignment_write_scope(self, metadata: dict[str, Any]) -> list[str]:
        allowed = self.assignment_scope_items(metadata.get("allowed_files"))
        ownership = metadata.get("ownership") if isinstance(metadata.get("ownership"), dict) else {}
        owned = self.assignment_scope_items(ownership.get("owned_files"))
        owned.extend(self.assignment_scope_items(ownership.get("owned_globs")))
        owned.extend(self.assignment_scope_items(metadata.get("allowed_globs")))
        result: list[str] = []
        seen: set[str] = set()
        for item in [*allowed, *owned]:
            key = self.assignment_path_key(item)
            if key not in seen:
                result.append(item)
                seen.add(key)
        return result

    def assignment_has_glob(self, value: str) -> bool:
        return any(char in value for char in "*?[")

    def assignment_allows_write_scope_overlap(self, metadata: dict[str, Any]) -> bool:
        non_overlap = metadata.get("non_overlap") if isinstance(metadata.get("non_overlap"), dict) else {}
        return str(non_overlap.get("policy") or "") == "allow_write_scope_overlap"

    def assignment_dependency_set(self, metadata: dict[str, Any]) -> set[str]:
        dependencies = metadata.get("dependencies") if isinstance(metadata.get("dependencies"), dict) else {}
        values = [
            *as_list(dependencies.get("blocked_by")),
            *as_list(metadata.get("dependencies") if not isinstance(metadata.get("dependencies"), dict) else []),
            *as_list(metadata.get("depends_on")),
        ]
        return {safe_id(str(item), "assignment") for item in values if item}

    def validate_assignment_required_sources(self, project_root: Path, contract: dict[str, Any]) -> list[str]:
        missing: list[str] = []
        required_sources = contract.get("context", {}).get("required_sources", [])
        for source in required_sources if isinstance(required_sources, list) else []:
            path = project_root / str(source)
            if not path.is_file():
                missing.append(str(source))
        artifacts = contract.get("context", {}).get("context_artifacts", [])
        for item in artifacts if isinstance(artifacts, list) else []:
            if isinstance(item, dict) and item.get("required", True):
                source = str(item.get("path", ""))
                if source and not (project_root / source).is_file():
                    missing.append(source)
        return sorted(set(missing))

    def capsule_coordination_block(self, snapshot: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        coordination = snapshot.get("workplace_coordination") if isinstance(snapshot.get("workplace_coordination"), dict) else {}
        effective_mode = str(coordination.get("effective_mode") or "simple")
        raw_requirements = metadata.get("coordination_requirements") if isinstance(metadata.get("coordination_requirements"), dict) else {}
        inbox_requirements = raw_requirements.get("director_inbox") if isinstance(raw_requirements.get("director_inbox"), dict) else {}
        submit_required = bool(inbox_requirements.get("required", False) or metadata.get("director_inbox_submit_required", False))
        if effective_mode != "organized":
            if submit_required:
                raise SystemExit("FAIL: assignment requires Director inbox but project effective coordination mode is simple")
            return {
                "effective_mode": "simple",
                "director_required": False,
                "director_available_at_workplace": bool(coordination.get("director_available_at_workplace", False)),
            }
        director_inbox = coordination.get("director_inbox") if isinstance(coordination.get("director_inbox"), dict) else {}
        return {
            "effective_mode": "organized",
            "director_required": bool(coordination.get("director_required", True)),
            "director_process": coordination.get("director_process") or "agent-director-supervision",
            "director_inbox": {
                "enabled": bool(director_inbox.get("enabled", True)),
                "submit_required": submit_required or bool(director_inbox.get("submit_required", False)),
                "allowed_message_types": director_inbox.get("allowed_message_types", ["worker_report", "error_report", "decision_request"]),
            },
        }

    def path_allowed_by_scope(self, path: str, scopes: list[str]) -> bool:
        key = self.assignment_path_key(path)
        for scope in scopes:
            scope_key = self.assignment_path_key(scope)
            if scope_key in {".pf/artifacts/**", ".pf/artifacts/*"} and key.startswith(".pf/artifacts/"):
                return True
            if self.assignment_has_glob(scope_key) and fnmatch.fnmatch(key, scope_key):
                return True
            if key == scope_key:
                return True
        return False

    def normalize_context_artifacts(self, value: Any) -> list[dict[str, Any]]:
        artifacts: list[dict[str, Any]] = []
        for item in self._list(value):
            if isinstance(item, dict):
                path = self.normalize_assignment_path(item.get('path'))
                if not path:
                    continue
                artifacts.append({'path': path, 'role': str(item.get('role', 'input')), 'required': bool(item.get('required', True)), 'mutable_by_worker': bool(item.get('mutable_by_worker', False))})
            else:
                path = self.normalize_assignment_path(item)
                if path:
                    artifacts.append({'path': path, 'role': 'input', 'required': True, 'mutable_by_worker': False})
        return artifacts

    def normalize_required_outputs(self, value: Any) -> list[dict[str, Any]]:
        outputs: list[dict[str, Any]] = []
        for item in self._list(value):
            if isinstance(item, dict):
                output_id = str(item.get('id') or item.get('name') or '').strip()
                if not output_id:
                    continue
                record = dict(item)
                record['id'] = output_id
                record.setdefault('type', 'unspecified')
                record.setdefault('required', True)
                outputs.append(record)
            else:
                text = str(item or '').strip()
                if not text:
                    continue
                if '=' in text:
                    record: dict[str, Any] = {}
                    for part in text.split(','):
                        if '=' not in part:
                            continue
                        key, raw_value = part.split('=', 1)
                        key = key.strip()
                        raw_value = raw_value.strip()
                        if key == 'required':
                            record[key] = raw_value.lower() not in {'0', 'false', 'no'}
                        else:
                            record[key] = raw_value
                    output_id = str(record.get('id') or record.get('name') or '').strip()
                    if output_id:
                        record['id'] = output_id
                        record.setdefault('type', 'unspecified')
                        record.setdefault('required', True)
                        outputs.append(record)
                    continue
                outputs.append({'id': text, 'type': 'unspecified', 'required': True})
        return outputs

    def normalize_execution_mode(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            mode = dict(value)
        elif isinstance(value, str) and value.strip():
            mode = {'kind': value.strip()}
        else:
            return {}
        kind = str(mode.get('kind', '')).strip()
        if kind:
            mode['kind'] = kind
        mode.setdefault('code_changes_allowed', False)
        mode.setdefault('artifact_changes_allowed', True)
        mode.setdefault('requires_review', True)
        return mode

    def normalize_ownership(self, metadata: dict[str, Any], allowed_files: list[str]) -> dict[str, Any]:
        raw = metadata.get('ownership') if isinstance(metadata.get('ownership'), dict) else {}
        owner_id = str(raw.get('owner_id') or metadata.get('id') or 'assignment')
        owned_files = self.assignment_scope_items(raw.get('owned_files'))
        owned_globs = self.assignment_scope_items(raw.get('owned_globs'))
        if not owned_files and allowed_files:
            owned_files = list(allowed_files)
        return {'owner_id': safe_id(owner_id, 'assignment'), 'owner_label': str(raw.get('owner_label') or f"worker-{safe_id(owner_id, 'assignment')}"), 'role': str(raw.get('role') or metadata.get('role') or ''), 'writer': bool(raw.get('writer', bool(allowed_files or owned_files or owned_globs))), 'owned_files': owned_files, 'owned_globs': owned_globs}

    def normalize_non_overlap(self, value: Any, current_write_scope: list[str]) -> dict[str, Any]:
        if not isinstance(value, dict):
            value = {}
        result = dict(value)
        active = result.get('active_parallel_tasks')
        if not isinstance(active, list):
            active = []
        if result.get('active_parallel_task'):
            active.append({'id': result.get('active_parallel_task'), 'owner': result.get('active_parallel_owner'), 'write_scope': self.assignment_scope_items(result.get('active_parallel_scope'))})
        normalized_active: list[dict[str, Any]] = []
        for item in active:
            if isinstance(item, dict):
                record = dict(item)
                if 'write_scope' in record:
                    record['write_scope'] = self.assignment_scope_items(record.get('write_scope'))
                normalized_active.append(record)
            elif item:
                normalized_active.append({'id': str(item), 'write_scope': []})
        result['policy'] = str(result.get('policy') or 'block_on_write_overlap')
        result['active_parallel_tasks'] = normalized_active
        result['current_write_scope'] = current_write_scope
        result.pop('active_parallel_task', None)
        result.pop('active_parallel_owner', None)
        result.pop('active_parallel_scope', None)
        return result

    def normalize_workspace_access(self, value: Any) -> dict[str, list[Any]]:
        raw = value if isinstance(value, dict) else {}
        aliases = {'knowledge': 'knowledge_resources', 'resources': 'knowledge_resources', 'knowledge_resource_refs': 'knowledge_resources', 'template_refs': 'templates', 'tool_refs': 'tools', 'mcp_refs': 'mcp', 'mcp_servers': 'mcp'}
        result: dict[str, list[Any]] = {key: [] for key in WORKSPACE_ACCESS_KEYS}
        for key, target in aliases.items():
            if key in raw:
                result[target].extend(self._list(raw.get(key)))
        for key in WORKSPACE_ACCESS_KEYS:
            result[key].extend(self._list(raw.get(key)))
        cleaned: dict[str, list[Any]] = {}
        for key, items in result.items():
            normalized: list[Any] = []
            seen: set[str] = set()
            for item in items:
                if isinstance(item, dict):
                    marker = json.dumps(item, sort_keys=True, ensure_ascii=False)
                    normalized_item: Any = {str(k): v for k, v in item.items()}
                else:
                    text = str(item).strip()
                    if not text:
                        continue
                    marker = text
                    normalized_item = text
                if marker in seen:
                    continue
                seen.add(marker)
                normalized.append(normalized_item)
            cleaned[key] = normalized
        return cleaned

    def workspace_access_public_path_issues(self, access: dict[str, list[Any]]) -> list[str]:
        issues: list[str] = []
        for group, items in access.items():
            for index, item in enumerate(items):
                if isinstance(item, str):
                    if self.path_string_is_absolute(item) or PATH_CONSTANT_PATTERN.search(item):
                        issues.append(f'workspace_access.{group}[{index}] must be an id/path_ref, not a private path')
                    continue
                if not isinstance(item, dict):
                    continue
                if 'path' in item or 'resolved_path' in item or 'absolute_path' in item:
                    issues.append(f'workspace_access.{group}[{index}] must not include raw path fields')
                for key, value in item.items():
                    if str(key) == 'path_ref':
                        continue
                    if isinstance(value, str) and (self.path_string_is_absolute(value) or PATH_CONSTANT_PATTERN.search(value)):
                        issues.append(f'workspace_access.{group}[{index}].{key} must not include a private path')
        return issues

    def normalize_subagent_policy(self, raw: Any) -> dict[str, Any]:
        source = raw if isinstance(raw, dict) else {}
        allow = bool(source.get('allow', source.get('allow_subagents', False)))
        max_subagents = int(source['max_subagents']) if 'max_subagents' in source else 1 if allow else 0
        reports_dir = self.normalize_assignment_path(str(source.get('reports_dir') or ''))
        return {'allow': allow, 'max_subagents': max_subagents, 'allowed_roles': [str(item) for item in self._list(source.get('allowed_roles'))], 'require_reports': bool(source.get('require_reports', source.get('require_subagent_reports', allow))), 'reports_dir': reports_dir}

    def normalize_agent_model(self, value: Any) -> str:
        if value in (None, ''):
            return ''
        text = str(value).strip()
        if not text:
            return ''
        if any((char in text for char in '\r\n\x00')):
            raise SystemExit('FAIL: agent model contains unsupported control characters')
        return text

    def normalize_agent_reasoning_effort(self, value: Any) -> str:
        if value in (None, ''):
            return ''
        text = str(value).strip().lower()
        if not text:
            return ''
        if text not in {'minimal', 'low', 'medium', 'high'}:
            raise SystemExit(f'FAIL: agent reasoning effort must be one of minimal, low, medium, high; got {text}')
        return text

    def path_string_is_absolute(self, value: str) -> bool:
        text = value.strip().replace('\\', '/')
        return bool(re.match('^[A-Za-z]:/', text) or text.startswith('/') or text.startswith('//'))

    def locate_flow_root(self, project_root: Path, *, prefer_pf: bool = True) -> Path:
        return ProjectMetadataReader(project_root, self.documents).flow_root(prefer_pf=prefer_pf)

    def project_context_snapshot_paths(self, project_root: Path) -> tuple[Path, Path]:
        contexts = self.locate_flow_root(project_root) / 'contexts'
        return (contexts / 'project-context.snapshot.yaml', contexts / 'project-context.snapshot.md')

    def project_id(self, project_root: Path) -> str:
        return ProjectMetadataReader(project_root, self.documents).project_id()
