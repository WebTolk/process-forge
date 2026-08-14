from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProcessCatalogContext:
    project_root: Path
    flow_root: Path
    distribution_root: Path
    active_official_pack_ids: frozenset[str]


@dataclass
class ProcessDefinitionRef:
    process_id: str
    path: Path
    process: dict[str, Any]
    origin: str
    root: Path
    catalog_role: str
    warnings: list[str]
    pack_id: str = ""
    active: bool = True
    available: bool = True
    production_ready: bool = False
