"""Hook selection and delivery payload construction."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import uuid

from ..common.clock import now_utc
from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader
from ..project.hooks import HookConfigurationReader


class HookDispatchPolicy:
    """Own the existing hook selection and payload algorithms."""

    def __init__(
        self,
        *,
        hooks: HookConfigurationReader | None = None,
        documents: YamlDocumentReader | None = None,
    ) -> None:
        self.hooks = hooks if hooks is not None else HookConfigurationReader()
        self.documents = documents if documents is not None else YamlDocumentReader(fallback=_parse_simple_yaml)

    def event_id_value(self, event: dict[str, Any]) -> str:
        return str(event.get("event_id") or event.get("id") or f"evt_{uuid.uuid4().hex}")

    def event_type_name(self, event: dict[str, Any]) -> str:
        return str(event.get("event_type") or event.get("type") or "")

    def event_matches_hook(self, event: dict[str, Any], hook: dict[str, Any]) -> bool:
        event_types = hook.get("event_types", ["*"])
        if not isinstance(event_types, list):
            return False
        return "*" in event_types or self.event_type_name(event) in event_types

    def hook_targets(self, project_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        config = self.documents.load(self.hooks.path(project_root))
        hooks_config = config.get("hooks") if isinstance(config, dict) else None
        if isinstance(hooks_config, dict):
            targets = hooks_config.get("targets", [])
            return hooks_config, targets if isinstance(targets, list) else []
        if isinstance(hooks_config, list):
            return {"mode": config.get("dispatch", {}).get("default_mode", "outbox") if isinstance(config.get("dispatch"), dict) else "outbox"}, hooks_config
        return {"mode": "outbox"}, []

    def selected_hooks(self, project_root: Path, event: dict[str, Any]) -> list[dict[str, Any]]:
        _hooks_config, hooks = self.hook_targets(project_root)
        selected: list[dict[str, Any]] = []
        for hook in hooks:
            if not isinstance(hook, dict):
                continue
            if not hook.get("enabled", False):
                continue
            if self.event_matches_hook(event, hook):
                selected.append(hook)
        return selected

    def hook_delivery_payload(self, event: dict[str, Any], target: dict[str, Any], mode: str, delivery_id: str) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "delivery_id": delivery_id,
            "delivery_time": now_utc(),
            "target_id": str(target.get("id", "hook")),
            "mode": mode,
            "event": event,
        }

    def wtaicc_outbox_payload(self, event: dict[str, Any], *, chat: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "target": "wtaicc",
            "delivery_mode": "outbox",
            "created_at": now_utc(),
            "event": event,
            "chat": chat or {"included": False, "mode": "metadata_only", "messages": []},
        }
