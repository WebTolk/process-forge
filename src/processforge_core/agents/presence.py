"""Live presence records and exact selection, without attendance authority."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from processforge_core.common.ids import opaque_identity_digest, safe_id


def _read_json(path: Path) -> object:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class AgentPresenceReader:
    workplace_root: Path

    @property
    def directory(self) -> Path:
        return self.workplace_root / "runtime" / "agent-presence"

    def legacy_path(self, agent_id: str) -> Path:
        return self.directory / f"{safe_id(agent_id, 'agent')}.json"

    def path(self, agent_id: str, session_id: str) -> Path:
        return self.directory / safe_id(agent_id, "agent") / f"session-{opaque_identity_digest(session_id)}.json"

    def paths(self) -> list[Path]:
        presence_dir = self.directory
        if not presence_dir.is_dir():
            return []
        return sorted([*presence_dir.glob("*.json"), *presence_dir.glob("*/*.json")])

    def records(self) -> list[dict[str, Any]]:
        rows: dict[tuple[str, str], tuple[bool, dict[str, Any]]] = {}
        for path in self.paths():
            item = _read_json(path)
            if isinstance(item, dict) and item:
                agent_id, session_id = str(item.get("agent_id") or ""), str(item.get("session_id") or "")
                canonical = self.path(agent_id, session_id)
                legacy = self.directory / safe_id(agent_id, "agent") / f"{safe_id(session_id, 'session')}.json"
                if path not in {canonical, legacy, self.legacy_path(agent_id)}:
                    continue
                key = (agent_id, session_id)
                is_canonical = path == canonical
                if key not in rows or is_canonical:
                    rows[key] = (is_canonical, item)
        return [item for _canonical, item in rows.values()]

    def find(
        self,
        *,
        agent_id: str | None = None,
        session_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        requested_agent_id = safe_id(agent_id, "agent") if agent_id is not None else None
        requested_session_id = str(session_id) if session_id is not None else None
        matches: list[dict[str, Any]] = []
        for item in self.records():
            if requested_agent_id is not None and item.get("agent_id") != requested_agent_id:
                continue
            if requested_session_id is not None and item.get("session_id") != requested_session_id:
                continue
            if project_id and str(item.get("project_id") or "") != project_id:
                continue
            matches.append(item)
        if len(matches) == 1:
            return matches[0]
        if not matches and requested_agent_id is not None and requested_session_id is None:
            legacy = _read_json(self.legacy_path(requested_agent_id))
            if (
                isinstance(legacy, dict)
                and legacy.get("agent_id") == requested_agent_id
                and (not project_id or str(legacy.get("project_id") or "") == project_id)
            ):
                return legacy
        return {}
