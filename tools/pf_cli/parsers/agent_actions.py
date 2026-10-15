"""Register additive, bounded action discovery commands."""

from __future__ import annotations

import argparse
from collections.abc import Callable


def _limit(value: str) -> int:
    number = int(value)
    if not 1 <= number <= 100:
        raise argparse.ArgumentTypeError("limit must be between 1 and 100")
    return number


def _offset(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("offset must be nonnegative")
    return number


class ActionsCommandParser:
    def __init__(self, *, execute: Callable[[argparse.Namespace], int]) -> None:
        self._execute = execute

    def register(self, add_parser: Callable[..., argparse.ArgumentParser]) -> None:
        actions = add_parser("actions", help="Discover supported PF actions without executing them.", allow_abbrev=False)
        operations = actions.add_subparsers(dest="actions_operation", required=True)
        for operation in ("list", "describe"):
            command = operations.add_parser(operation, allow_abbrev=False)
            # Keep discovery selectors out of eager CLI project diagnostics.
            # ActionsCommand validates their completeness before any project read.
            command.add_argument("--project-root", dest="actions_project_root", help="Explicit project root; required only with Work selectors.")
            command.add_argument("--run", dest="actions_run", help="Exact Run id; supply with --assignment and --context-id.")
            command.add_argument("--assignment", dest="actions_assignment", help="Exact Assignment id.")
            command.add_argument("--context-id", dest="actions_context_id", help="Exact immutable Work context id.")
            command.add_argument("--json", action="store_true", help="Print JSON.")
            if operation == "list":
                command.add_argument("--query", default="", help="Filter action IDs and summaries (at most 256 characters).")
                command.add_argument("--surface", choices=["cli", "mcp"], default="")
                command.add_argument("--limit", type=_limit, default=25, help="Page size, 1..100 (default: 25).")
                command.add_argument("--offset", type=_offset, default=0, help="Nonnegative result offset.")
            else:
                command.add_argument("--action-id", required=True, help="Exact cli:<command path> or mcp:<tool name>.")
            command.set_defaults(func=self._execute)
