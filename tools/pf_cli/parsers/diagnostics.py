"""Register the existing diagnostic CLI command family."""

from __future__ import annotations

import argparse
from collections.abc import Callable

from processforge_core import diagnostics


class DiagnosticsCommandParser:
    """Bind diagnostic command arguments to the supplied handlers."""

    def __init__(
        self,
        *,
        configure: Callable[[argparse.Namespace], int],
        status: Callable[[argparse.Namespace], int],
        export: Callable[[argparse.Namespace], int],
    ) -> None:
        self._configure = configure
        self._status = status
        self._export = export

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        configure = add_parser(
            "diagnostics-configure",
            help="Plan or apply a bounded diagnostic profile change.",
        )
        configure.add_argument("--project-root", required=True)
        configure.add_argument(
            "--profile", choices=list(diagnostics.PROFILES), required=True
        )
        configure.add_argument(
            "--duration", type=int, default=600,
            help="Detailed profile lifetime in seconds (1..900).",
        )
        configure_scope = configure.add_mutually_exclusive_group()
        configure_scope.add_argument("--run-id")
        configure_scope.add_argument("--session-id")
        configure.add_argument("--apply", action="store_true")
        configure.set_defaults(func=self._configure)
        diagnostic_status = add_parser(
            "diagnostics-status",
            help="Inspect optional diagnostic configuration and local health "
            "without repairs.",
        )
        diagnostic_status.add_argument("--project-root", required=True)
        diagnostic_status.add_argument("--run-id")
        diagnostic_status.add_argument("--session-id")
        diagnostic_status.set_defaults(func=self._status)
        diagnostic_export = add_parser(
            "diagnostics-export",
            help="Create a bounded sanitized local diagnostic bundle; "
            "no repair or upload.",
        )
        diagnostic_export.add_argument("--project-root", required=True)
        diagnostic_export.add_argument("--output", required=True)
        diagnostic_export.add_argument("--request-id")
        diagnostic_export.add_argument("--run-id")
        diagnostic_export.add_argument("--since")
        diagnostic_export.add_argument("--until")
        diagnostic_export.set_defaults(func=self._export)
