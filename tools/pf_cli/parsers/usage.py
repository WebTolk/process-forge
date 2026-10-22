"""Register explicit scoped accounting queries and receipt import/replay."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class UsageCommandParser:
    """Expose the common usage service through one discoverable CLI family."""

    def __init__(self, *, execute: Callable[[argparse.Namespace], int]) -> None:
        self._execute = execute

    def register(self, add_parser: Callable[..., argparse.ArgumentParser]) -> None:
        """Register query filters and bounded explicit-file collection commands."""
        parser = add_parser(
            "usage",
            help="Query PF token/activity accounting or import explicit receipts (JSON).",
        )
        commands = parser.add_subparsers(dest="usage_command", required=True)
        for name in (
            "projects",
            "summary",
            "details",
            "project",
            "task",
            "run",
            "attempt",
            "collect",
            "import",
            "replay",
        ):
            command = commands.add_parser(name)
            command.add_argument("--project-root", required=True)
            command.add_argument(
                "--workplace",
                help="Existing workplace directory or manifest; defaults to project configuration.",
            )
            command.add_argument(
                "--json", action="store_true", help="Always returns one JSON object."
            )
            if name in ("collect", "import", "replay"):
                command.add_argument(
                    "--file",
                    required=True,
                    help="Explicit bounded JSONL source; never scans histories.",
                )
                command.add_argument(
                    "--binding",
                    required=True,
                    help="Versioned exact source/session/project manifest.",
                )
                command.add_argument(
                    "--timing",
                    help="Optional managed attempt timing sidecar for replay.",
                )
            else:
                command.add_argument(
                    "--scope",
                    choices=("project", "workplace"),
                    default="project",
                    help="Workplace requires explicit local human invocation; unavailable in managed workers.",
                )
                command.add_argument("--project-id")
                command.add_argument(
                    "--task", dest="assignment_id", required=name in ("task", "attempt")
                )
                command.add_argument(
                    "--run", dest="run_id", required=name in ("run", "attempt")
                )
                command.add_argument("--attempt", type=int, required=name == "attempt")
                command.add_argument("--source-id")
                command.add_argument("--model")
                command.add_argument(
                    "--start", help="Inclusive aware UTC ISO timestamp."
                )
                command.add_argument("--end", help="Exclusive aware UTC ISO timestamp.")
                command.add_argument("--limit", type=int, default=100)
                command.add_argument("--offset", type=int, default=0)
                command.add_argument(
                    "--kind", choices=("usage", "activity"), default="usage"
                )
            command.set_defaults(func=self._execute)
