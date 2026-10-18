"""Publish existing immutable assignment capsules through explicit dependencies."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Protocol

if TYPE_CHECKING:
    from ..ports import ProjectSnapshotReadPort


class ContextFieldsBuilder(Protocol):
    """Existing context builder with project, Core and workplace already bound."""

    def __call__(
        self,
        assignment_path: Path,
        assignment: dict[str, Any],
        snapshot: dict[str, Any],
        *,
        pin: dict[str, Any],
        run_record: dict[str, Any],
    ) -> dict[str, Any]: ...


@dataclass(frozen=True, kw_only=True)
class AssignmentCapsulePublisher:
    """Own the existing exclusive capsule write without owning grants or locks."""

    project_root: Path
    flow_root: Callable[[], Path]
    assignment_path: Callable[[str], Path]
    snapshot_reader: Callable[[], ProjectSnapshotReadPort]
    build_context_fields: ContextFieldsBuilder
    now_utc: Callable[[], str]
    dump_yaml: Callable[[dict[str, Any]], str]
    ensure_trailing_newline: Callable[[str], str]
    relative_path: Callable[[Path, Path], str]
    sha256_file: Callable[[Path], str]
    stable_ids: Callable[[Any], list[str]]

    def publish(self, run: dict[str, Any], assignment: dict[str, Any], pin: dict[str, Any]) -> tuple[str, str]:
        from .context import ContextContractError

        path = self.flow_root() / "contexts" / "assignment-capsules" / f"{assignment['id']}.capsule.yaml"
        if path.exists():
            raise ContextContractError("immutable_context_exists", remediation="create_successor_work")
        snapshot = self.snapshot_reader().load()
        fields = self.build_context_fields(self.assignment_path(assignment["id"]), assignment,
                                           snapshot, pin=pin, run_record=run)
        capsule = {
            "schema_version": 1,
            "capsule": {"id": f"{assignment['id']}-capsule", "generated_at": self.now_utc(), "assignment_id": assignment["id"], "assignment_path": f".pf/assignments/{assignment['id']}.yaml", "immutable": True, "worker_may_rebuild_context": False},
            "context_snapshot": {"id": pin["snapshot_id"], "sha256": pin["snapshot_checksum"], "freshness_at_creation": "fresh"},
            **fields,
        }
        capsule["context"].update(freshness="fresh", selected_specializations=self.stable_ids(assignment.get("selected_specializations")), applied_project_overrides=[])
        capsule["assignment"]["stage"] = assignment["stage"]
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(self.ensure_trailing_newline(self.dump_yaml(capsule)))
        except FileExistsError as exc:
            raise ContextContractError("immutable_context_exists", remediation="create_successor_work") from exc
        return self.relative_path(path, self.project_root), "sha256:" + self.sha256_file(path)
