"""Live coordination configuration reads through concrete Core readers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader
from .metadata import ProjectMetadataReader

COORDINATION_PROJECT_MODES = {"inherit", "simple", "organized"}
WORKPLACE_DEFAULT_PROJECT_MODES = {"simple", "organized"}
DIRECTOR_OFFICE_DEFAULTS = {
    "process_id": "agent-director-supervision",
    "scope": "workplace",
    "office_path": ".pf/director",
    "inbox_path": ".pf/director/inbox",
    "outbox_path": ".pf/director/outbox",
    "cases_path": ".pf/director/cases",
    "runs_path": ".pf/director/runs",
    "artifacts_path": ".pf/director/artifacts",
    "history_path": ".pf/director/history",
    "continuations_path": ".pf/director/continuations",
    "runtime_path": ".pf/director/runtime",
}


@dataclass(frozen=True)
class ProjectCoordinationReader:
    documents: YamlDocumentReader = field(
        default_factory=lambda: YamlDocumentReader(_parse_simple_yaml),
    )

    def project_mode(self, value: Any) -> str:
        mode = str(value or "inherit").strip().lower()
        if mode not in COORDINATION_PROJECT_MODES:
            raise SystemExit("FAIL: project coordination mode must be inherit, simple, or organized")
        return mode

    def workplace_mode(self, value: Any) -> str:
        mode = str(value or "simple").strip().lower()
        if mode not in WORKPLACE_DEFAULT_PROJECT_MODES:
            raise SystemExit("FAIL: workplace default_project_mode must be simple or organized")
        return mode

    def workplace_defaults(self) -> dict[str, Any]:
        return {
            "director_enabled": False,
            "director_office_enabled": False,
            "default_project_mode": "simple",
            "director": dict(DIRECTOR_OFFICE_DEFAULTS),
            "error_workflow_support": True,
        }

    def project_defaults(self, mode: str = "inherit") -> dict[str, Any]:
        return {
            "mode": self.project_mode(mode),
            "director": {
                "use_workplace_director": True,
                "inbox_submit_required": False,
            },
        }

    def workplace(self, workplace_manifest: Path | None) -> dict[str, Any]:
        config = self.workplace_defaults()
        if workplace_manifest and workplace_manifest.is_file():
            data = self.documents.load(workplace_manifest)
            raw = data.get("coordination") if isinstance(data, dict) else None
            if isinstance(raw, dict):
                config.update({key: value for key, value in raw.items() if key != "director"})
                if isinstance(raw.get("director"), dict):
                    director = dict(DIRECTOR_OFFICE_DEFAULTS)
                    director.update(raw["director"])
                    config["director"] = director
        config["director_enabled"] = bool(config.get("director_enabled", False))
        config["director_office_enabled"] = bool(config.get("director_office_enabled", False))
        config["default_project_mode"] = self.workplace_mode(config.get("default_project_mode"))
        if not isinstance(config.get("director"), dict):
            config["director"] = dict(DIRECTOR_OFFICE_DEFAULTS)
        return config

    def project(self, project_root: Path) -> dict[str, Any]:
        flow_root = ProjectMetadataReader(project_root).flow_root()
        manifest = flow_root / "process-forge.yaml"
        data = self.documents.load(manifest) if manifest.is_file() else {}
        raw = data.get("coordination") if isinstance(data, dict) else None
        config = self.project_defaults()
        if isinstance(raw, dict):
            config.update({key: value for key, value in raw.items() if key != "director"})
            director = config.get("director") if isinstance(config.get("director"), dict) else {}
            if isinstance(raw.get("director"), dict):
                director = dict(director)
                director.update(raw["director"])
            config["director"] = director
        config["mode"] = self.project_mode(config.get("mode"))
        if not isinstance(config.get("director"), dict):
            config["director"] = self.project_defaults()["director"]
        config["director"].setdefault("use_workplace_director", True)
        config["director"].setdefault("inbox_submit_required", False)
        return config
