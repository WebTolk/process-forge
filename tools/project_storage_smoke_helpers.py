"""Create project storage for hand-authored smoke manifests."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def create_fixture_flow(project: Path) -> Path:
    from processforge_core.maintenance.fresh_project import create_project_storage_root

    project.mkdir(parents=True, exist_ok=True)
    create_project_storage_root(project)
    return project / ".pf"


def initialize_fixture_storage(project: Path, workplace: Path | None = None) -> None:
    from processforge_core.configuration import ConfigurationProvider, PFConfig
    from processforge_core.maintenance.fresh_project import initialize_project_storage

    if not initialize_project_storage(
        project, workplace, configuration=ConfigurationProvider.pinned(PFConfig())
    ):
        raise AssertionError("expected a fresh smoke project")
