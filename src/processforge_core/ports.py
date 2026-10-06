"""Internal structural dependency contracts; not a stable public API."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator, Protocol

__all__ = ()


class ProcessDefinitionReadPort(Protocol):
    """Effective definition and pin status; not selection or transition authority."""

    def effective_process(self, run: dict[str, Any]) -> tuple[dict[str, Any], str]: ...


class WorkReadCorePort(Protocol):
    def locate_flow_root(self, project_root: Path) -> Path: ...

    def load_yaml_document(self, path: Path) -> dict[str, Any]: ...


class WorkRecordReadPort(Protocol):
    """Raw live records; consumers validate identity and select Work."""

    def runs(self) -> Iterator[tuple[Path, dict[str, Any]]]: ...

    def load_run(self, run_id: str) -> dict[str, Any]: ...

    def load_assignment(self, assignment_id: str) -> dict[str, Any]: ...


class WorkContextReadPort(Protocol):
    """Existing context read results; not a permission or lifecycle authority."""

    def validation(self, assignment: dict[str, Any]) -> dict[str, Any]: ...

    def normalized_assignment(self, assignment: dict[str, Any]) -> dict[str, Any]: ...
