"""Read and validate current project hook configuration."""

from __future__ import annotations

from pathlib import Path

from ..common.checks import Check, check
from ..common.paths import rel
from ..common.yaml_io import _parse_simple_yaml, yaml_error
from ..documents.reader import YamlDocumentReader
from .metadata import ProjectMetadataReader


class HookConfigurationReader:
    """Own hook paths and checks without dispatching hook effects."""

    def __init__(self) -> None:
        self.documents = YamlDocumentReader(_parse_simple_yaml)

    def path(self, project_root: Path) -> Path:
        return ProjectMetadataReader(project_root, documents=self.documents).flow_root() / "hooks.yaml"

    def validate(self, project_root: Path) -> list[Check]:
        path = self.path(project_root)
        checks: list[Check] = []
        if not path.is_file():
            return [check("FAIL", f"{rel(path, project_root)} missing")]
        data = self.documents.load(path)
        error = yaml_error(data)
        if error:
            return [check("FAIL", f"{rel(path, project_root)} is invalid YAML: {error}")]
        hooks_config = data.get("hooks") if isinstance(data, dict) else None
        if not isinstance(hooks_config, dict):
            return [check("FAIL", f"{rel(path, project_root)} missing hooks object")]
        targets = hooks_config.get("targets")
        if not isinstance(targets, list):
            checks.append(check("FAIL", f"{rel(path, project_root)} hooks.targets must be a list"))
            return checks
        checks.append(check("PASS", f"{rel(path, project_root)} is valid YAML"))
        checks.append(check("PASS", f"{rel(path, project_root)} hooks.targets is a list"))
        for index, target in enumerate(targets):
            label = f"hooks.targets[{index}]"
            if not isinstance(target, dict):
                checks.append(check("FAIL", f"{label} must be an object"))
                continue
            for key in ["id", "type", "enabled", "event_types"]:
                checks.append(check("PASS" if key in target else "FAIL", f"{label}.{key} present"))
            event_types = target.get("event_types")
            if isinstance(event_types, list) and all(isinstance(item, str) and item for item in event_types):
                checks.append(check("PASS", f"{label}.event_types is a string list"))
            else:
                checks.append(check("FAIL", f"{label}.event_types must be a string list; quote wildcard as \"*\""))
        return checks
