"""Register existing CLI commands for monitor."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class MonitorCommandParser:
    """Register the existing monitor command family."""

    def __init__(
        self,
        *,
        runtime_monitor: Callable[[argparse.Namespace], int],
        interval_parser: Callable[[str], float],
    ) -> None:
        self._runtime_monitor = runtime_monitor
        self._interval_parser = interval_parser

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        monitor = add_parser("monitor", help="Observe local Runtime without starting, stopping, or changing it.")
        monitor.add_argument("--workplace", required=True, help="Existing workplace root directory.")
        monitor.add_argument("--once", action="store_true", help="Print one plain snapshot and exit.")
        monitor.add_argument("--json", action="store_true", help="Print one allowlisted JSON snapshot without terminal controls.")
        monitor.add_argument("--interval", type=self._interval_parser, default=None, help="Viewer interval override (1 to 60); default follows Runtime configuration.")
        monitor.add_argument("--details", action="store_true", help="Show detailed scheduler and observation diagnostics.")
        monitor.add_argument("--ascii", action="store_true", help="Use ASCII-only terminal text.")
        monitor.add_argument("--no-color", action="store_true", help="Disable color (the monitor is monochrome by default).")
        monitor.set_defaults(func=self._runtime_monitor)
