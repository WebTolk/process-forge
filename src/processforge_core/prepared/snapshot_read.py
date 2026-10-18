"""Existing pinned/current snapshot reads for prepared resource admission."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ..project.context_read import ProjectContextCheck


@dataclass(frozen=True, kw_only=True)
class PreparedResourceSnapshotReader:
    flow_root: Callable[[], Callable[[Path], Path]] = field(repr=False, compare=False)
    snapshot_paths: Callable[[], Callable[[Path], tuple[Path, Path]]] = field(repr=False, compare=False)
    bounded_yaml: Callable[[], Callable[[Path, Path, str], tuple[dict[str, Any], str]]] = field(repr=False, compare=False)
    current_snapshot: Callable[[], Callable[[Path], dict[str, Any]]] = field(repr=False, compare=False)
    context_checker: Callable[[], ProjectContextCheck] = field(repr=False, compare=False)
    selector_pattern: Callable[[], re.Pattern[str]] = field(repr=False, compare=False)
    fail: Callable[[], Callable[[str], None]] = field(repr=False, compare=False)

    def load(
        self, project: Path, capsule: dict[str, Any], contract: dict[str, Any],
        workplace: Path,
    ) -> tuple[dict[str, Any], dict[str, Any], str, str]:
        flow_root = self.flow_root()(project).resolve()
        current_path, _ = self.snapshot_paths()(project)
        try:
            current, current_checksum = self.bounded_yaml()(current_path, flow_root, "snapshot_unavailable")
            current_from_garage = self.current_snapshot()(project)
        except (OSError, RuntimeError, SystemExit, TypeError, AttributeError):
            self.fail()("snapshot_unavailable")
        if current != current_from_garage:
            self.fail()("snapshot_changed_during_preparation")

        check = self.context_checker()(project, explicit_workplace=str(workplace))
        if not isinstance(check, dict) or check.get("status") not in {"fresh", "fresh_with_updates"}:
            self.fail()("snapshot_not_fresh")

        pinned = capsule.get("context_snapshot")
        contract_snapshot = contract.get("snapshot")
        if not isinstance(pinned, dict) or not isinstance(contract_snapshot, dict):
            self.fail()("work_context_mismatch")
        snapshot_id, expected_checksum = str(pinned.get("id") or ""), str(pinned.get("sha256") or "")
        if (not self.selector_pattern().fullmatch(snapshot_id) or not expected_checksum.startswith("sha256:")
                or contract_snapshot != {"id": snapshot_id, "checksum": expected_checksum}):
            self.fail()("work_context_mismatch")

        generations = flow_root / "contexts" / "project-context.snapshots"
        generation_path = generations / f"{snapshot_id}.yaml"
        if generation_path.exists() or generation_path.is_symlink():
            pinned_snapshot, pinned_checksum = self.bounded_yaml()(generation_path, flow_root, "snapshot_generation_changed")
            if pinned_checksum != expected_checksum:
                self.fail()("snapshot_generation_changed")
        elif current_checksum == expected_checksum:
            pinned_snapshot = current
            pinned_checksum = current_checksum
        else:
            self.fail()("snapshot_generation_missing")

        return pinned_snapshot, current, snapshot_id, expected_checksum

