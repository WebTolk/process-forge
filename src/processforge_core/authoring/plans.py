from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..common.paths import rel


@dataclass
class AuthoringWrite:
    destination: Path
    content: bytes | None
    role: str = "entity"
    operation: str = "create"
    schema_name: str | None = None
    allow_replace: bool = False

@dataclass
class AuthoringEffect:
    label: str
    destination: str
    role: str = "audit"
    operation: str = "append"
    condition: str = "after_commit"
    kind: str = "callback"
    payload: dict[str, Any] = field(default_factory=dict)
    executable: bool = True
    callback: Any = None

@dataclass
class AuthoringPlan:
    transaction_id: str
    command: str
    runtime_root: Path
    authoritative_writes: list[AuthoringWrite]
    registry_writes: list[AuthoringWrite]
    post_commit_effects: list[AuthoringEffect]
    validation_callbacks: list[Any]


class AuthoringPlanRenderer:
    def render(self, plan: AuthoringPlan, root: Path) -> None:
        print(f"PLAN: {plan.command}")
        print("TRANSACTION: <generated-on-apply>")
        rows: list[tuple[str, str, str, str]] = []
        for write in [*plan.authoritative_writes, *plan.registry_writes]:
            rows.append(
                (
                    rel(write.destination, root),
                    write.role,
                    write.operation,
                    f"schema={write.schema_name}" if write.schema_name else "",
                )
            )
        for effect in plan.post_commit_effects:
            rows.append((effect.destination, effect.role, effect.operation, effect.condition))
        for destination, role, operation, condition in sorted(rows):
            suffix = f" [{condition}]" if condition else ""
            print(f"- {role}:{operation}: {destination}{suffix}")
