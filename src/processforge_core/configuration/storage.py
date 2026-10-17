"""Port for revision-checked configuration persistence."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import PFConfig, ProjectPFConfig


@dataclass(frozen=True)
class ConfigSnapshot:
    config: PFConfig | ProjectPFConfig
    revision: str | None

    @property
    def exists(self) -> bool:
        return self.revision is not None


class ConfigStore(Protocol):
    def read(self) -> ConfigSnapshot: ...

    def write(self, config: PFConfig | ProjectPFConfig, *, expected_revision: str | None) -> ConfigSnapshot: ...

    def delete(self, *, expected_revision: str) -> ConfigSnapshot: ...
