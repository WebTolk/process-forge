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

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        parser = add_parser("config", help="Manage the selected workplace configuration through Core CRUD.")
        commands = parser.add_subparsers(dest="config_command", required=True)
        for name in ("create", "read", "update", "delete"):
            command = commands.add_parser(name)
            command.add_argument("--workplace", required=True, help="Workplace directory or workplace.yaml.")
            command.add_argument("--json", action="store_true", help="Return one JSON object.")
            if name in {"read", "update", "delete"}:
                command.add_argument("--key", required=name == "update", help="Dotted setting name; delete with a key resets it to its default.")
            if name == "update":
                command.add_argument("--value", required=True, help="New value as JSON, for example 2.")
            if name in {"update", "delete"}:
                command.add_argument("--if-revision", help="Reject a stale client revision returned by read.")
            command.set_defaults(func=self._execute)
