"""Register existing CLI commands for egress."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class EgressCommandParser:
    """Register the existing egress command family."""

    def __init__(
        self,
        *,
        execute: Callable[[argparse.Namespace], int],
    ) -> None:
        self._execute = execute

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        parser = add_parser("egress", help="Qualify and operate explicit v2 managed disclosure mediation.")
        commands = parser.add_subparsers(dest="egress_command", required=True)
        for name in ("bind", "qualify", "status", "run", "export", "revoke", "prune"):
            item = commands.add_parser(name)
            item.set_defaults(func=lambda args: self._execute(args))
            item.add_argument("--project-root", required=name != "bind")
            if name in {"bind", "run", "export", "revoke"}:
                item.add_argument("--policy", required=True, help="Trusted local operator policy JSON.")
            if name != "bind":
                item.add_argument("--store-root", required=True, help="External owner-only .pf-egress-private directory.")
            if name == "bind":
                item.add_argument("--predecessor", help="Preserved predecessor assignment id; requires project root.")
            if name in {"run", "export"}:
                item.add_argument("--assignment", required=True)
                item.add_argument("--attempt", type=int, required=True)
            if name == "run":
                item.add_argument("--rounds", type=int, default=16)
                item.add_argument("--credential-file", help="Owner-only transport credential, never model input.")
            if name == "export":
                item.add_argument("--output", required=True, help="New derivative; existing files are never replaced.")
