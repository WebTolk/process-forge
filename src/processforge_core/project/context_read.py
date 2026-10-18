"""Live execution project reads with explicit operation dependencies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


class ProjectContextCheck(Protocol):
    def __call__(
        self, project_root: Path, *, explicit_workplace: str | None = None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True, kw_only=True)
class ExecutionProjectReadService:
    project_root: Path
    workplace_root: Path | None
    context_checker: Callable[[], ProjectContextCheck] = field(repr=False, compare=False)
    document_loader: Callable[[], Callable[[Path], dict[str, Any]]] = field(repr=False, compare=False)
    flow_root: Callable[[], Path] = field(repr=False, compare=False)

    def context_check(self) -> dict[str, Any]:
        explicit = ""
        if self.workplace_root and (self.workplace_root / "workplace.yaml").is_file():
            explicit = str(self.workplace_root)
        return self.context_checker()(self.project_root, explicit_workplace=explicit or None)

    def manifest(self) -> dict[str, Any]:
        return self.document_loader()(self.flow_root() / "process-forge.yaml")
