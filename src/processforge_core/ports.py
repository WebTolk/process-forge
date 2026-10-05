"""Internal structural dependency contracts; not a stable public API."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

__all__ = ()


class WorkReadCorePort(Protocol):
    def locate_flow_root(self, project_root: Path) -> Path: ...

    def load_yaml_document(self, path: Path) -> dict[str, Any]: ...
