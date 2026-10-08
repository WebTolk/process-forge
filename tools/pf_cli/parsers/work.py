"""Register existing CLI commands for work."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class WorkCommandParser:
    """Register the existing work command family."""

    def __init__(
        self,
        *,
        work_cancel: Callable[[argparse.Namespace], int],
        work_resource_read: Callable[[argparse.Namespace], int],
        work_start: Callable[[argparse.Namespace], int],
        work_state: Callable[[argparse.Namespace], int],
        work_transition: Callable[[argparse.Namespace], int],
    ) -> None:
        self._work_cancel = work_cancel
        self._work_resource_read = work_resource_read
        self._work_start = work_start
        self._work_state = work_state
        self._work_transition = work_transition

    def register_start(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        work_start = add_parser("work-start", help="Start or continue declarative governed work.")
        work_start.add_argument("--project-root", required=True, help="Project root path.")
        work_start.add_argument("--workplace", help="Workplace root override.")
        work_start.add_argument("--objective", required=True, help="High-level work objective.")
        work_start.add_argument("--process-id", help="Optional allowed process id for the new governed work.")
        work_start.add_argument("--egress-intent", help="Explicit trusted v2 intent JSON created by egress bind; existing capsules stay immutable.")
        work_start.add_argument("--scope-file", help="Explicit local operator assignment-scope JSON (version 1, max 64 KiB); pinned before creation, never applied to an existing context.")
        work_start.add_argument("--json", action="store_true", help="Print JSON.")
        work_start.set_defaults(func=self._work_start)

    def register_state_resources_transition_cancel(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        work_state = add_parser("work-state", help="Read current declarative governed work state.")
        work_state.add_argument("--project-root", required=True, help="Project root path.")
        work_state.add_argument("--workplace", help="Workplace root override.")
        work_state.add_argument("--run", help="Explicit Run id.")
        work_state.add_argument("--assignment", help="Explicit Assignment id.")
        work_state.add_argument("--context-id", help="Expected Work context id.")
        work_state.add_argument("--session", help="Use this session's explicit continuation selection.")
        work_state.add_argument("--json", action="store_true", help="Print JSON.")
        work_state.set_defaults(func=self._work_state)

        for work_read_name in ("work-search", "work-resolve"):
            work_read = add_parser(work_read_name, help="Read verified resources of an explicitly selected immutable Work context.")
            work_read.add_argument("--project-root", required=True)
            work_read.add_argument("--workplace")
            work_read.add_argument("--run", required=True)
            work_read.add_argument("--assignment", required=True)
            work_read.add_argument("--context-id", required=True)
            work_read.add_argument("--json", action="store_true")
            if work_read_name == "work-search":
                work_read.add_argument("--query", required=True)
                work_read.add_argument("--limit", type=int)
                work_read.add_argument("--limitstart", type=int)
                work_read.add_argument("--offset", type=int)
            else:
                work_read.add_argument("--resource-id", required=True)
            work_read.set_defaults(func=self._work_resource_read)

        work_transition = add_parser("work-transition", help="Advance declarative governed work using outcome and evidence.")
        work_transition.add_argument("--project-root", required=True, help="Project root path.")
        work_transition.add_argument("--workplace", help="Workplace root override.")
        work_transition.add_argument("--run", help="Explicit Run id.")
        work_transition.add_argument("--assignment", help="Explicit Assignment id.")
        work_transition.add_argument("--context-id", help="Expected Work context id.")
        work_transition.add_argument("--session", help="Use this session's explicit continuation selection.")
        work_transition.add_argument("--outcome", required=True, help="Declared stage outcome.")
        work_transition.add_argument("--evidence", action="append", default=[], help="Evidence JSON object or attestation text. Repeatable.")
        work_transition.add_argument("--evidence-file", help="JSON file containing one evidence object or an array.")
        work_transition.add_argument("--notes", help="Optional transition notes.")
        work_transition.add_argument("--json", action="store_true", help="Print JSON.")
        work_transition.set_defaults(func=self._work_transition)

        work_cancel = add_parser("work-cancel", help="Preview or apply cancellation of one exact Work; preserve history and capsule.")
        work_cancel.add_argument("--project-root", required=True)
        work_cancel.add_argument("--workplace")
        work_cancel.add_argument("--run", required=True)
        work_cancel.add_argument("--assignment", required=True)
        work_cancel.add_argument("--context-id", required=True)
        work_cancel.add_argument("--capsule-checksum", required=True)
        work_cancel.add_argument("--reason", required=True)
        work_cancel.add_argument("--evidence", action="append", default=[])
        work_cancel.add_argument("--apply", action="store_true")
        work_cancel.add_argument("--json", action="store_true")
        work_cancel.set_defaults(func=self._work_cancel)
