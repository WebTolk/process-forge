"""Existing hook outbox dispatch, result recording and runtime path resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..common.ids import safe_id
from ..common.paths import rel
from ..project.metadata import PROJECT_FLOW_ROOT
from ..work.context_documents import ContextContractInputs
from .hook_outbox import delivery_key, publish_outbox, write_receipt
from .hook_policy import HookDispatchPolicy


@dataclass(frozen=True)
class RuntimeHookDispatcher:
    policy: HookDispatchPolicy = field(default_factory=HookDispatchPolicy)
    inputs: ContextContractInputs = field(default_factory=ContextContractInputs)

    def hook_results_root(self, project_root: Path) -> Path:
        return (
            self.inputs.locate_flow_root(project_root) / "runtime" / "hooks" / "results"
        )

    def resolve_runtime_config_path(
        self, project_root: Path, value: str | None, default: Path
    ) -> Path:
        if not value:
            return default
        path = Path(value)
        if path.is_absolute():
            return path
        if path.parts and path.parts[0] == PROJECT_FLOW_ROOT:
            return project_root / path
        return self.inputs.locate_flow_root(project_root) / path

    def write_hook_result(self, project_root: Path, result: dict[str, Any]) -> Path:
        # A later skipped command must not replace a completed outbox receipt.
        suffix = ".skipped.json" if result["status"] == "skipped" else ".json"
        target = (
            self.hook_results_root(project_root) / f"{result['delivery_id']}{suffix}"
        )
        return write_receipt(target, result)

    def dispatch_hooks(
        self,
        project_root: Path,
        event: dict[str, Any],
        *,
        dry_run: bool = False,
        outbox: bool = True,
        targets: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        hooks = (
            self.policy.selected_hooks(project_root, event)
            if targets is None
            else targets
        )
        actions: list[dict[str, Any]] = []
        event_id = self.policy.event_id_value(event)
        if not (event.get("event_id") or event.get("id")):
            event = {**event, "event_id": event_id}
        first_error: OSError | ValueError | None = None
        for hook in hooks:
            try:
                action = self._dispatch_hook(
                    project_root, event, event_id, hook, dry_run=dry_run, outbox=outbox
                )
            except (OSError, ValueError) as error:
                # Keep the event pending, but attempt its other admitted routes.
                if first_error is None:
                    first_error = error
            else:
                actions.append(action)
        if first_error is not None:
            raise first_error
        return actions

    def _dispatch_hook(
        self,
        project_root: Path,
        event: dict[str, Any],
        event_id: str,
        hook: dict[str, Any],
        *,
        dry_run: bool,
        outbox: bool,
    ) -> dict[str, Any]:
        hook_id = str(hook.get("id", "hook"))
        hook_type = str(hook.get("type", "outbox"))
        delivery_id = delivery_key(event_id, hook_id)
        action: dict[str, Any] = {
            "hook": hook_id,
            "target_id": hook_id,
            "type": hook_type,
            "delivery_id": delivery_id,
        }
        if dry_run:
            action["status"] = "dry_run"
            action["mode"] = "dry_run"
        elif (
            hook_type in {"outbox", "file_outbox", "webhook", "webhook_future"}
            and outbox
        ):
            default_outbox = (
                self.inputs.locate_flow_root(project_root)
                / "runtime"
                / "hooks"
                / "outbox"
            )
            target_root = self.resolve_runtime_config_path(
                project_root,
                str(hook.get("path") or hook.get("outbox") or ""),
                default_outbox,
            )
            wtaicc = safe_id(hook_id, "hook").startswith("wtaicc")
            if wtaicc and target_root.name != "wtaicc":
                target_root = target_root / "wtaicc"
            if wtaicc:
                payload = self.policy.wtaicc_outbox_payload(event)
                payload.update(target_id=hook_id, delivery_id=delivery_id)
            else:
                payload = self.policy.hook_delivery_payload(
                    event, hook, "outbox", delivery_id
                )
            key, outbox_path, result_path = publish_outbox(
                project_root,
                target_root,
                self.hook_results_root(project_root),
                event_id,
                hook_id,
                delivery_id,
                payload,
            )
            action["status"] = "outbox_written"
            action.update(delivery_id=key, outbox=outbox_path, result=result_path)
        elif hook_type == "command":
            action["status"] = "skipped"
            action["reason"] = (
                "command hooks require an explicit future runner/executor"
            )
            result = {
                "schema_version": 1,
                "delivery_id": delivery_id,
                "target_id": hook_id,
                "status": "skipped",
                "exit_code": 0,
                "blocking": bool(hook.get("blocking", False)),
                "message": action["reason"],
            }
            action["result"] = rel(
                self.write_hook_result(project_root, result), project_root
            )
        elif hook_type == "webhook" and (
            not self.policy.hook_targets(project_root)[0].get(
                "network_send_enabled", False
            )
        ):
            action["status"] = "skipped"
            action["reason"] = "network send is disabled by default"
        else:
            action["status"] = "skipped"
            action["reason"] = f"unsupported hook type: {hook_type}"
        return action
