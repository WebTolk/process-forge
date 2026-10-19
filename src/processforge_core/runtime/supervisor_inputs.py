from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from processforge_core.common.clock import now_utc
from processforge_core.common.yaml_io import _parse_simple_yaml
from processforge_core.documents.reader import YamlDocumentReader
from processforge_core.common.json_io import json_write
from processforge_core.work.context_documents import ContextContractInputs
from processforge_core.work.paths import WorkPaths


class SupervisorStateInputs:
    def __init__(
        self,
        documents: YamlDocumentReader | None = None,
        inputs: ContextContractInputs | None = None,
        work_paths: WorkPaths | None = None,
    ) -> None:
        self.documents = documents if documents is not None else YamlDocumentReader(_parse_simple_yaml)
        self.inputs = inputs if inputs is not None else ContextContractInputs()
        self.work_paths = work_paths if work_paths is not None else WorkPaths()

    def load_run_plan_if_present(self, project_root: Path, run_id: str) -> dict[str, Any]:
        path = self.work_paths.run_root(project_root, run_id) / 'orchestrator-plan.yaml'
        return self.documents.read(path) if path.is_file() else {}

    def supervisor_state_path(self, project_root: Path) -> Path:
        return self.inputs.locate_flow_root(project_root) / 'runtime' / 'supervisor' / "state.json"

    def write_supervisor_state(self, project_root: Path, state: dict[str, Any]) -> None:
        state["updated_at"] = now_utc()
        json_write(self.supervisor_state_path(project_root), state)


@dataclass(frozen=True)
class SupervisorInputService(SupervisorStateInputs):
    distribution_root: Path
    documents: YamlDocumentReader = field(
        default_factory=lambda: YamlDocumentReader(_parse_simple_yaml),
    )
    inputs: ContextContractInputs = field(default_factory=ContextContractInputs)
    work_paths: WorkPaths = field(default_factory=WorkPaths)

    def default_supervisor_profile(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "id": "default",
            "title": "Default Process Supervisor",
            "loop": {"interval_seconds": 1, "max_ticks": 1},
            "scheduling": {"max_parallel_workers": 1, "start_policy": "manual", "default_driver": "manual"},
            "collection": {"auto_collect_completed": True},
            "stop": {"file": ".pf/runtime/supervisor/stop.request"},
        }

    def load_supervisor_profile(self, project_root: Path, profile_ref: str | None = None) -> dict[str, Any]:
        if not profile_ref or profile_ref == "default":
            template = self.distribution_root / "templates" / "supervisor-profile.yaml"
            return self.documents.read(template) if template.is_file() else self.default_supervisor_profile()
        path = Path(profile_ref).expanduser()
        if not path.is_absolute():
            path = (project_root / path).resolve()
        return self.documents.read(path)
