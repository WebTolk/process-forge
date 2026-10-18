"""Execute the existing Agent Entry CLI operations."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path


class AgentEntryCommand:
    """Adapt the existing entry-operation dispatch to Core use cases."""

    def execute(self, args: argparse.Namespace) -> int:
        from processforge_core.agent_entry.contract import EntryError, decode_json
        from processforge_core.agent_entry.migration import apply_entry, check_entry, plan_entry, rollback_entry
        from processforge_core.agent_entry.profiles import diagnose_entry, load_profiles
        from processforge_core.agent_entry.adapters import adapter_guide, apply_adapter, plan_adapter

        def input_json(name: str, maximum: int):
            with Path(name).expanduser().open("rb") as stream:
                return decode_json(stream.read(maximum + 1), maximum)

        try:
            operation = args.entry_operation
            project = Path(args.project_root) if args.project_root else None
            if operation == "profiles":
                result = load_profiles()
            elif operation == "adapter-plan":
                policy = input_json(args.budget_file, 65536) if args.budget_file else None
                result = plan_adapter(project, profile_id=args.profile, route=args.route, budget_policy=policy)
            elif operation == "adapter-apply":
                result = apply_adapter(project, input_json(args.plan_file, 262144), apply=args.apply)
            elif operation == "adapter-guide":
                observed = input_json(args.observations_file, 65536) if args.observations_file else None
                result = adapter_guide(project, profile_id=args.profile, route=args.route, cwd=args.cwd, observation=observed)
            elif operation == "diagnose":
                observed = input_json(args.observations_file, 65536) if args.observations_file else None
                result = diagnose_entry(project, profile_id=args.profile, observation=observed, cwd=args.cwd)
            elif operation in {"plan", "check"}:
                policy = input_json(args.budget_file, 65536) if args.budget_file else None
                result = (plan_entry if operation == "plan" else check_entry)(project, budget_policy=policy)
            elif operation == "apply":
                result = apply_entry(project, input_json(args.plan_file, 262144), apply=args.apply)
            else:
                result = rollback_entry(project, args.transaction, apply=args.apply)
        except EntryError as exc:
            result = {"action": "blocked", "reason": exc.reason}
            if exc.path:
                result["path"] = exc.path
        except OSError:
            result = {"action": "blocked", "reason": "storage_error"}
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 1 if result.get("action") in {"blocked", "incomplete"} or result.get("blockers") else 0


class AgentStartPromptCommand:
    """Render, plan or apply the existing guarded start prompt."""

    def __init__(
        self,
        *,
        require_flow_root: Callable[[Path], Path],
        start_prompt_renderer: Callable[[Path], str],
    ) -> None:
        self._require_flow_root = require_flow_root
        self._start_prompt_renderer = start_prompt_renderer

    def execute(self, args: argparse.Namespace) -> int:
        from processforge_core.agent_entry.contract import EntryError
        from processforge_core.agent_entry.migration import plan_start_prompt, apply_start_prompt
        project_root = Path(args.project_root).expanduser().absolute()
        flow_root = self._require_flow_root(project_root)
        if not getattr(args, "plan", False) and not getattr(args, "apply", False):
            print(self._start_prompt_renderer(project_root).rstrip())
            return 0
        try:
            if flow_root != project_root / ".pf":
                raise EntryError("unsupported_flow_root")
            plan = plan_start_prompt(project_root)
            result = apply_start_prompt(project_root, plan, apply=True) if getattr(args, "apply", False) else plan
        except EntryError as exc:
            print(json.dumps({"status": "conflict", "reason": exc.reason, "path": exc.path}, ensure_ascii=False, indent=2))
            return 1
        except OSError:
            print(json.dumps({"status": "conflict", "reason": "storage_error"}))
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("action") == "incomplete" or result.get("blockers") else 0
