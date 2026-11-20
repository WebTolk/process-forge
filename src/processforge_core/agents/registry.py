from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from processforge_core.common.clock import now_utc
from processforge_core.common.yaml_io import _parse_simple_yaml
from processforge_core.documents.reader import YamlDocumentReader
from processforge_core.agents.presence import AgentPresenceReader
from processforge_core.common.yaml_io import write_yaml_file, yaml_error


@dataclass(frozen=True)
class AgentWorkplaceRegistry:
    documents: YamlDocumentReader = field(
        default_factory=lambda: YamlDocumentReader(_parse_simple_yaml),
    )

    def workplace_agent_registry_path(self, workplace_root: Path) -> Path:
        return workplace_root / "registries" / "agents.yaml"

    def workplace_agent_ledger_path(self, workplace_root: Path) -> Path:
        return workplace_root / "runtime" / "agent-ledger" / "sessions.ndjson"

    def workplace_agent_presence_dir(self, workplace_root: Path) -> Path:
        return AgentPresenceReader(workplace_root).directory

    def workplace_agent_leases_dir(self, workplace_root: Path) -> Path:
        return workplace_root / "runtime" / "agent-leases"

    def ensure_agent_workplace_dirs(self, workplace_root: Path) -> None:
        for path in [
            workplace_root / "registries",
            workplace_root / "runtime" / "agent-ledger",
            self.workplace_agent_presence_dir(workplace_root),
            self.workplace_agent_leases_dir(workplace_root),
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def load_agent_registry(self, workplace_root: Path) -> dict[str, Any]:
        path = self.workplace_agent_registry_path(workplace_root)
        data = self.documents.load(path)
        if yaml_error(data) or not data:
            return {"schema_version": 1, "agents": []}
        data.setdefault("schema_version", 1)
        data.setdefault("agents", [])
        return data

    def save_agent_registry(self, workplace_root: Path, data: dict[str, Any]) -> None:
        self.ensure_agent_workplace_dirs(workplace_root)
        write_yaml_file(self.workplace_agent_registry_path(workplace_root), data)

    def append_agent_ledger_event(self, workplace_root: Path, payload: dict[str, Any]) -> None:
        self.ensure_agent_workplace_dirs(workplace_root)
        payload.setdefault("schema_version", 1)
        payload.setdefault("recorded_at", now_utc())
        path = self.workplace_agent_ledger_path(workplace_root)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
