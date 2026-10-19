from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from processforge_core.common.clock import now_utc
from processforge_core.common.yaml_io import _parse_simple_yaml
from processforge_core.documents.reader import YamlDocumentReader
from processforge_core.common.ids import safe_id
from processforge_core.common.json_io import json_read
from processforge_core.common.yaml_io import write_yaml_file
from processforge_core.project.coordination import DIRECTOR_OFFICE_DEFAULTS, ProjectCoordinationReader
from processforge_core.project.snapshot_sources import local_workplace_manifest_reference
from processforge_core.work.context_documents import ContextContractInputs


@dataclass(frozen=True)
class ProjectCoordinationStateService:
    documents: YamlDocumentReader = field(
        default_factory=lambda: YamlDocumentReader(_parse_simple_yaml),
    )
    inputs: ContextContractInputs = field(default_factory=ContextContractInputs)
    coordination_reader: ProjectCoordinationReader = field(default_factory=ProjectCoordinationReader)

    def active_organized_project_sessions(self, workplace_root: Path) -> list[dict[str, Any]]:
        active: list[dict[str, Any]] = []
        presence_root = workplace_root / "runtime" / "agent-presence"
        presence_paths = [*presence_root.glob("*.json"), *presence_root.glob("*/*.json")]
        for presence_path in sorted(presence_paths):
            try:
                data = json_read(presence_path)
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                # Presence is observational. A partially-written or legacy record
                # must not make workplace-mode inspection unusable.
                continue
            if not isinstance(data, dict):
                continue
            if data.get("status") != "online":
                continue
            project_root_value = data.get("project_root")
            if not project_root_value:
                continue
            project_root = Path(str(project_root_value)).expanduser()
            if not project_root.is_dir():
                continue
            try:
                status = self.effective_project_coordination(project_root, str(workplace_root))
            except SystemExit:
                continue
            if status.get("effective_mode") == "organized":
                active.append({"agent_id": data.get("agent_id"), "session_id": data.get("session_id"), "project_root": str(project_root.resolve()).replace('\\', '/')})
        return active

    def update_workplace_coordination(self, workplace_root: Path, updater: Any) -> dict[str, Any]:
        manifest = workplace_root / "workplace.yaml"
        if not manifest.is_file():
            raise SystemExit(f"FAIL: workplace.yaml missing: {manifest}")
        data = self.documents.read(manifest)
        cfg = self.coordination_reader.workplace(manifest)
        updater(cfg)
        data["coordination"] = cfg
        write_yaml_file(manifest, data)
        return cfg

    def director_message_payload(self, workplace_root: Path, project_root: Path | None, message_type: str, content: str, coordination: dict[str, Any]) -> dict[str, Any]:
        project_payload = None
        if project_root:
            project_payload = {
                "id": self.inputs.project_id(project_root),
                "root": str(project_root).replace('\\', '/'),
                "effective_mode": coordination.get("effective_mode"),
            }
        return {
            "schema_version": 1,
            "id": f"msg-{uuid.uuid4().hex[:16]}",
            "created_at": now_utc(),
            "message_type": message_type,
            "status": "open",
            "scope": "project" if project_root else "workspace",
            "project": project_payload,
            "content": content,
        }

    def director_inbox_project_ids(self, workplace_root: Path) -> set[str]:
        ids: set[str] = set()
        inbox = self.director_office_paths(workplace_root).get("inbox_path")
        if not inbox or not inbox.is_dir():
            return ids
        for path in inbox.glob("*.yaml"):
            data = self.documents.load(path)
            project_data = data.get("project") if isinstance(data, dict) else None
            if isinstance(project_data, dict) and project_data.get("id"):
                ids.add(str(project_data["id"]))
        return ids

    def normalize_workplace_path(self, path: Path) -> Path:
        resolved = path.expanduser().resolve()
        if resolved.name == "workplace.yaml":
            return resolved.parent
        return resolved

    def workplace_manifest_path_from_root(self, workplace: Path) -> Path:
        root = self.normalize_workplace_path(workplace)
        return root if root.name == "workplace.yaml" else root / "workplace.yaml"

    def resolve_workplace_manifest(self, local_manifest: Path) -> Path | None:
        workplace = local_workplace_manifest_reference(local_manifest.read_text(encoding="utf-8", errors="replace"))
        if not workplace:
            return None
        if not workplace.is_absolute():
            workplace = (local_manifest.parent / workplace).resolve()
        return workplace

    def resolve_project_workplace_manifest(self, project_root: Path, explicit_workplace: str | None = None) -> Path | None:
        if explicit_workplace:
            candidate = self.workplace_manifest_path_from_root(Path(explicit_workplace))
            return candidate if candidate.is_file() else candidate
        flow_root = self.inputs.locate_flow_root(project_root)
        local_config = flow_root / "process-forge.local.yaml"
        if local_config.is_file():
            return self.resolve_workplace_manifest(local_config)
        manifest = flow_root / "process-forge.yaml"
        if manifest.is_file():
            data = self.documents.load(manifest)
            workplace_data = data.get("workplace") if isinstance(data, dict) else None
            if isinstance(workplace_data, dict) and workplace_data.get("reference") == "auto":
                return project_root / "workplace.yaml" if (project_root / "workplace.yaml").is_file() else None
        return None

    def director_office_paths(self, workplace_root: Path, coordination: dict[str, Any] | None = None) -> dict[str, Path]:
        cfg = coordination or self.coordination_reader.workplace(workplace_root / "workplace.yaml")
        director = cfg.get("director") if isinstance(cfg.get("director"), dict) else {}
        paths: dict[str, Path] = {}
        for key, default in DIRECTOR_OFFICE_DEFAULTS.items():
            if not key.endswith("_path"):
                continue
            raw = str(director.get(key) or default)
            path = Path(raw)
            paths[key] = path if path.is_absolute() else workplace_root / path
        return paths

    def director_office_exists(self, workplace_root: Path, coordination: dict[str, Any] | None = None) -> bool:
        paths = self.director_office_paths(workplace_root, coordination)
        required = ["office_path", "inbox_path", "outbox_path", "cases_path", "history_path"]
        return all(paths[key].is_dir() for key in required)

    def effective_project_coordination(self, project_root: Path, explicit_workplace: str | None = None) -> dict[str, Any]:
        project_cfg = self.coordination_reader.project(project_root)
        workplace_manifest = self.resolve_project_workplace_manifest(project_root, explicit_workplace)
        workplace_root = workplace_manifest.parent if workplace_manifest else None
        workplace_cfg = self.coordination_reader.workplace(workplace_manifest)
        project_mode = self.coordination_reader.project_mode(project_cfg.get("mode"))
        default_mode = self.coordination_reader.workplace_mode(workplace_cfg.get("default_project_mode"))
        effective_mode = default_mode if project_mode == "inherit" else project_mode
        director_available = bool(workplace_cfg.get("director_enabled"))
        office_exists = bool(workplace_root and self.director_office_exists(workplace_root, workplace_cfg))
        director_required = effective_mode == "organized"
        result = {
            "project_root": str(project_root).replace('\\', '/'),
            "project_id": self.inputs.project_id(project_root) if (self.inputs.locate_flow_root(project_root) / "process-forge.yaml").is_file() else safe_id(project_root.name, "project"),
            "project_mode": project_mode,
            "workplace_root": str(workplace_root).replace('\\', '/') if workplace_root else None,
            "workplace_manifest": str(workplace_manifest).replace('\\', '/') if workplace_manifest else None,
            "workplace_default_project_mode": default_mode,
            "workplace_director_enabled": director_available,
            "workplace_director_office_enabled": bool(workplace_cfg.get("director_office_enabled")),
            "director_office_exists": office_exists,
            "effective_mode": effective_mode,
            "director_available": director_available,
            "director_required": director_required,
            "director_process": str((workplace_cfg.get("director") or {}).get("process_id") or "agent-director-supervision"),
            "director_inbox": {
                "enabled": bool(director_available and effective_mode == "organized"),
                "submit_required": bool((project_cfg.get("director") or {}).get("inbox_submit_required", False)) if effective_mode == "organized" else False,
                "allowed_message_types": ["worker_report", "error_report", "decision_request"] if effective_mode == "organized" else ["operator_note"],
            },
        }
        if workplace_root:
            paths = self.director_office_paths(workplace_root, workplace_cfg)
            result["director_office"] = {key: str(value).replace('\\', '/') for key, value in paths.items()}
        return result
