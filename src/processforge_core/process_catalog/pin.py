"""Existing ProcessPinReadService responsibilities with explicit operation dependencies."""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


from ..ports import ProjectSnapshotReadPort

@dataclass(frozen=True, kw_only=True)
class ProcessPinReadService:
    project_root: Path = field(repr=False, compare=False)
    flow_root: Callable[[], Path] = field(repr=False, compare=False)
    snapshots: Callable[[], ProjectSnapshotReadPort] = field(repr=False, compare=False)
    fingerprint: Callable[[Any], str] = field(repr=False, compare=False)
    stable_ids: Callable[[Any], list[str]] = field(repr=False, compare=False)

    def pin(self, process: dict[str, Any], source_path: Path, *, active_specializations: list[str], selected_resource_ids: list[str], allowed_processes: list[str]) -> dict[str, Any]:
        snapshot_path = self.flow_root() / 'contexts' / 'project-context.snapshot.yaml'
        snapshot = self.snapshots().load(snapshot_path)
        meta = snapshot.get('snapshot') if isinstance(snapshot.get('snapshot'), dict) else {}
        snapshot_checksum = self.snapshots().checksum(snapshot_path)
        normalized = json.loads(json.dumps(process, ensure_ascii=False))
        try:
            process_source = source_path.resolve().relative_to(self.project_root.resolve()).as_posix()
        except ValueError:
            process_source = f"catalog:{normalized.get('id') or source_path.stem}"
        return {'process_id': str(normalized.get('id') or ''), 'process_version': str(normalized.get('version') or ''), 'process_fingerprint': self.fingerprint(normalized), 'process_source': process_source, 'snapshot_id': str(meta.get('id') or ''), 'snapshot_checksum': snapshot_checksum, 'definition': normalized, 'active_specializations': active_specializations, 'selected_resource_ids': selected_resource_ids, 'allowed_processes': allowed_processes}

    def selected_resource_ids(self) -> list[str]:
        snapshot = self.snapshots().load()
        resolved = snapshot.get('resolved') if isinstance(snapshot.get('resolved'), dict) else {}
        return sorted(self.stable_ids(resolved.get('knowledge_resources')))
