from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from processforge_core.common.clock import now_utc
from processforge_core.common.paths import rel
from processforge_core.common.text import ensure_trailing_newline
from processforge_core.common.yaml_dump import dump_yaml
from processforge_core.project.metadata import PROJECT_FLOW_ROOT
from processforge_core.work.context_documents import ContextContractInputs


@dataclass(frozen=True)
class SessionMetadataWriter:
    inputs: ContextContractInputs = field(default_factory=ContextContractInputs)

    def write_workplace_context_snapshot(self, project_root: Path, snapshot: dict[str, Any]) -> Path:
        cache = self.inputs.locate_flow_root(project_root) / "runtime" / "cache"
        cache.mkdir(parents=True, exist_ok=True)
        local_config = self.inputs.locate_flow_root(project_root) / "process-forge.local.yaml"
        payload = {
            "schema_version": 1,
            "snapshot": {
                "id": "workplace-context",
                "generated_at": now_utc(),
                "privacy": "private",
            },
            "project": {"id": self.inputs.project_id(project_root)},
            "flow": {
                "root": PROJECT_FLOW_ROOT,
                "manifest": rel(self.inputs.locate_flow_root(project_root) / "process-forge.yaml", project_root),
                "local_config": rel(local_config, project_root),
                "local_config_exists": local_config.is_file(),
            },
            "capabilities": snapshot.get("capabilities", {}),
            "resolved_parameters": snapshot.get("resolved_parameters", {}),
            "parameter_resolution": snapshot.get("parameter_resolution", {}),
            "workplace_coordination": snapshot.get("workplace_coordination", {}),
            "tools": snapshot.get("tools", {}),
            "mcp": snapshot.get("mcp", {}),
            "notes": ["Private runtime snapshot may include local availability state."],
        }
        target = cache / "workplace-context.snapshot.yaml"
        target.write_text(ensure_trailing_newline(dump_yaml(payload)), encoding="utf-8")
        return target

    def session_runtime_paths(self, project_root: Path, session_id: str) -> tuple[Path, Path]:
        runtime = self.inputs.locate_flow_root(project_root) / "runtime"
        return runtime / "sessions" / f"{session_id}.yaml", runtime / "telemetry" / f"{session_id}.ndjson"

    def write_session_metadata(self, project_root: Path, session_id: str, mode: str, snapshot_status: str, telemetry_path: Path) -> Path:
        session_path, _events_path = self.session_runtime_paths(project_root, session_id)
        snapshot_yaml, _snapshot_md = self.inputs.project_context_snapshot_paths(project_root)
        payload = {
            "schema_version": 1,
            "session": {
                "id": session_id,
                "mode": mode,
                "actor_type": "human_started_agent",
                "role": "orchestrator",
                "started_at": now_utc(),
            },
            "context": {
                "project_flow_root": PROJECT_FLOW_ROOT,
                "snapshot": rel(snapshot_yaml, project_root),
                "snapshot_status": snapshot_status,
            },
            "telemetry": {"events": rel(telemetry_path, project_root)},
        }
        session_path.parent.mkdir(parents=True, exist_ok=True)
        session_path.write_text(ensure_trailing_newline(dump_yaml(payload)), encoding="utf-8")
        return session_path
