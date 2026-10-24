"""Register existing CLI commands for configuration."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class ConfigurationCommandParser:
    """Register the existing configuration command family."""

    def __init__(
        self,
        *,
        execute: Callable[[argparse.Namespace], int],
    ) -> None:
        self._execute = execute

    def register(self, add_parser: Callable[..., argparse.ArgumentParser]) -> None:
        parser = add_parser(
            "config",
            help="Manage the selected workplace configuration through Core CRUD.",
        )
        commands = parser.add_subparsers(dest="config_command", required=True)
        for name in ("create", "read", "update", "delete"):
            command = commands.add_parser(name)
            scope = command.add_mutually_exclusive_group(required=True)
            scope.add_argument(
                "--workplace", help="Workplace directory or workplace.yaml."
            )
            scope.add_argument(
                "--device", action="store_true", help="Manage the full device PFConfig."
            )
            command.add_argument(
                "--project-root",
                help="Manage this project's configuration overrides; null inherits the workplace value.",
            )
            command.add_argument(
                "--json", action="store_true", help="Return one JSON object."
            )
            if name in {"read", "update", "delete"}:
                command.add_argument(
                    "--key",
                    required=name == "update",
                    help="Dotted setting name; delete with a key resets it to its default.",
                )
            if name == "update":
                command.add_argument(
                    "--value", required=True, help="New value as JSON, for example 2."
                )
            if name in {"update", "delete"}:
                command.add_argument(
                    "--if-revision",
                    help="Reject a stale client revision returned by read.",
                )
            command.set_defaults(func=self._execute)
