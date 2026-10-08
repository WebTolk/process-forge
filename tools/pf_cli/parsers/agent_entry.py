"""Register existing CLI commands for agent entry."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class AgentEntryCommandParser:
    """Register the existing agent entry command family."""

    def __init__(
        self,
        *,
        agent_entry: Callable[[argparse.Namespace], int],
        agent_start_prompt: Callable[[argparse.Namespace], int],
        global_agents_section: Callable[[argparse.Namespace], int],
    ) -> None:
        self._agent_entry = agent_entry
        self._agent_start_prompt = agent_start_prompt
        self._global_agents_section = global_agents_section

    def register_global_section(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        global_agents = add_parser("global-agents-section", help="Insert or update the bounded ProcessForge section in an agent instructions file.")
        global_agents.add_argument("--path", required=True, help="Path to AGENTS.md, CODEX.md, or another agent instruction file.")
        global_agents.add_argument("--dry-run", action="store_true", help="Write a .candidate file instead of changing the target.")
        global_agents.add_argument("--force", action="store_true", help="Update the target file in place.")
        global_agents.set_defaults(func=self._global_agents_section)

    def register_prompt(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        agent_start_prompt = add_parser("agent-start-prompt", help="Preview current startup guidance; placement requires --apply.")
        agent_start_prompt.add_argument("--project-root", required=True, help="Project root path.")
        start_mode = agent_start_prompt.add_mutually_exclusive_group()
        start_mode.add_argument("--plan", action="store_true", help="Print the read-only placement plan as JSON.")
        start_mode.add_argument("--apply", action="store_true", help="Explicitly place recognized PF-owned START text with a rollback journal.")
        agent_start_prompt.set_defaults(func=self._agent_start_prompt)

    def register_operations(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        entry = add_parser("agent-entry", help="Inspect entry profiles, diagnose actual files, or explicitly migrate the startup contract.")
        entry_commands = entry.add_subparsers(dest="entry_operation", required=True)
        for operation in ("plan", "check", "apply", "rollback", "diagnose", "profiles", "adapter-plan", "adapter-apply", "adapter-guide"):
            entry_command = entry_commands.add_parser(operation)
            entry_command.add_argument("--project-root", required=operation != "profiles")
            entry_command.add_argument("--json", action="store_true", help="JSON is always emitted by this command.")
            if operation in {"adapter-plan", "adapter-guide"}:
                entry_command.add_argument("--profile", required=True, help="Exact id from agent-entry profiles.")
                entry_command.add_argument("--route", required=True, choices=["root-agents", "native-import", "explicit-read", "prerequisites"])
            if operation in {"plan", "check", "adapter-plan"}:
                entry_command.add_argument("--budget-file", help="Explicit generic instruction-accounting policies JSON.")
            elif operation in {"diagnose", "adapter-guide"}:
                if operation == "diagnose":
                    entry_command.add_argument("--profile", required=True, help="Exact id from agent-entry profiles.")
                entry_command.add_argument("--cwd", default=".", help="Project-relative client working directory; no directory change.")
                entry_command.add_argument("--observations-file", help="Bounded explicit settings/context observations JSON; never host certification.")
            elif operation in {"apply", "rollback", "adapter-apply"}:
                entry_command.add_argument("--apply", action="store_true", help="Explicit acknowledgement of filesystem writes.")
                if operation in {"apply", "adapter-apply"}:
                    entry_command.add_argument("--plan-file", required=True)
                else:
                    entry_command.add_argument("--transaction", required=True)
            entry_command.set_defaults(func=self._agent_entry)
