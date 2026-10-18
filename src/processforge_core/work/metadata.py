"""Explicit, operation-local Work metadata reads; YAML remains authoritative."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader
from .inventory import WorkInventory


RUN_FIELDS = ("id", "status", "process", "objective", "tasks", "created_at", "updated_at", "__yaml_error__")
ASSIGNMENT_FIELDS = ("id", "run_id", "status", "stage", "process", "objective", "session", "created_at", "updated_at", "__yaml_error__")


@dataclass
class WorkMetadataReadPass:
    """Share observed facts only within one read operation, never across writes.

    Acquisition is lazy to preserve the consumer's read/error order. All returned
    documents are independent copies; only compact parsing results survive in
    the existing content-addressed process cache after this pass is released.
    """

    project_root: Path
    documents: YamlDocumentReader = field(default_factory=lambda: YamlDocumentReader(_parse_simple_yaml))
    _paths: tuple[Path, ...] | None = field(default=None, init=False, repr=False)
    _values: dict[tuple[Path, tuple[str, ...]], dict[str, Any]] = field(default_factory=dict, init=False, repr=False)
    _exists: dict[Path, bool] = field(default_factory=dict, init=False, repr=False)

    @property
    def flow_root(self) -> Path:
        return self.project_root / ".pf"

    def runs(self) -> Iterator[tuple[Path, dict[str, Any]]]:
        if self._paths is None:
            self._paths = tuple(WorkInventory(self.flow_root, self.documents.load).run_paths())
        for path in self._paths:
            yield path, self._read(path, RUN_FIELDS)

    def assignment_path(self, assignment_id: str) -> Path:
        return self.flow_root / "assignments" / f"{assignment_id}.yaml"

    def assignment_exists(self, assignment_id: str) -> bool:
        path = self.assignment_path(assignment_id)
        if path not in self._exists:
            self._exists[path] = path.is_file()
        return self._exists[path]

    def assignment(self, assignment_id: str) -> dict[str, Any]:
        return self._read(self.assignment_path(assignment_id), ASSIGNMENT_FIELDS)

    def _read(self, path: Path, fields: tuple[str, ...]) -> dict[str, Any]:
        if type(self.documents) is not YamlDocumentReader:
            return self.documents.load(path)
        key = path, fields
        if key not in self._values:
            value = self.documents.load_fields(path, fields)
            # An unknown-fields-only mapping is still a nonempty document.
            # Keep unusual documents on the original path without retaining
            # an entire history in this pass just to preserve truthiness.
            if not value:
                return self.documents.load(path)
            self._values[key] = copy.deepcopy(value)
        return copy.deepcopy(self._values[key])

    def completion_inputs(
        self, path: Path, run: dict[str, Any], assignment: dict[str, Any], entry_id: str, *,
        valid_id: Callable[[str], bool], load_assignment: Callable[[str], dict[str, Any]],
        intent_path: Callable[[str], Path],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Keep journal validation with its existing owner and full live inputs."""
        run_id = str(run.get("id") or "")
        assignment_id = str(assignment.get("id") or "")
        if (valid_id(run_id) and valid_id(assignment_id)
                and intent_path(run_id).is_file()):
            return self.documents.load(path), load_assignment(entry_id)
        return run, assignment
