"""Select runtime drivers using current project and saved worker inputs."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from ..common.ids import safe_id
from ..common.json_io import json_read
from ..project.metadata import ProjectMetadataReader
from ..work.paths import WorkPaths
from .catalog import RuntimeDriverCatalogReader
from .drivers import RuntimeDriverDefinitionPolicy


class RuntimeDriverSelectionService:
    def __init__(self, distribution_root: Path) -> None:
        self.catalog = RuntimeDriverCatalogReader(distribution_root)
        self.definition_policy = RuntimeDriverDefinitionPolicy()
        self.paths = WorkPaths()

    def for_task(self, project_root: Path, task: dict[str, Any], driver_arg: str | None = None) -> dict[str, Any]:
        driver_id = driver_arg or str(task.get("runtime_driver") or "manual")
        workplace_manifest = ProjectMetadataReader(project_root).workplace_manifest()
        driver = self.catalog.resolve(driver_id, workplace_manifest=workplace_manifest, project_root=project_root)
        if driver_arg and self.catalog.ref_is_direct_path(driver_arg):
            driver = copy.deepcopy(driver)
            driver["_driver_ref"] = self.catalog.normalized_ref(driver_arg, project_root)
        failures = [item.message for item in self.definition_policy.validate(driver) if item.level == "FAIL"]
        if failures:
            raise SystemExit("FAIL: runtime driver invalid: " + "; ".join(failures))
        return driver

    def for_worker_state(self, project_root: Path, task: dict[str, Any], state: dict[str, Any], fallback_driver_ref: str | None = None) -> dict[str, Any]:
        task_id = safe_id(str(task.get("id") or state.get("task_id") or "task"), "task")
        run_id = safe_id(str(task.get("run_id") or state.get("run_id") or "run"), "run")
        command = json_read(self.paths.worker_run(project_root, run_id, task_id)["command"])
        driver_ref = command.get("driver_ref")
        if isinstance(driver_ref, str) and driver_ref.strip():
            try:
                return self.for_task(project_root, task, driver_ref.strip())
            except SystemExit as exc:
                raise SystemExit(f"FAIL: saved runtime driver_ref invalid for {run_id}/{task_id}: {driver_ref}: {exc}") from exc
        driver_id = str(state.get("driver_id") or fallback_driver_ref or task.get("runtime_driver") or "manual")
        return self.for_task(project_root, task, driver_id)
