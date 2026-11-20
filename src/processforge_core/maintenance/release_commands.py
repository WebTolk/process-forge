"""Release command record shared by command planning and execution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReleaseCommand:
    label: str
    command: list[str]
    timeout: int
    allow_warn: bool = False
    layer: str = "public"
    public_gate: bool = True
