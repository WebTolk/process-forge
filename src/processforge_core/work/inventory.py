"""Raw live Work discovery; selection and validation belong to consumers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator


@dataclass(frozen=True)
class WorkInventory:
    flow_root: Path
    load_document: Callable[[Path], dict[str, Any]]

    def runs(self) -> Iterator[tuple[Path, dict[str, Any]]]:
        root = self.flow_root / "runs"
        for path in sorted(root.glob("*/run.yaml")) if root.is_dir() else []:
            yield path, self.load_document(path)

    def assignment_path(self, assignment_id: str) -> Path:
        return self.flow_root / "assignments" / f"{assignment_id}.yaml"

    def assignment(self, assignment_id: str) -> dict[str, Any]:
        return self.load_document(self.assignment_path(assignment_id))
