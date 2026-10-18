"""Register existing CLI commands for continuation."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class ContinuationCommandParser:
    """Register the existing continuation command family."""

    def __init__(
        self,
        *,
        continuation_create: Callable[[argparse.Namespace], int],
        continuation_doctor: Callable[[argparse.Namespace], int],
        continuation_resume: Callable[[argparse.Namespace], int],
        continuation_status: Callable[[argparse.Namespace], int],
    ) -> None:
        self._continuation_create = continuation_create
        self._continuation_doctor = continuation_doctor
        self._continuation_resume = continuation_resume
        self._continuation_status = continuation_status

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        continuation_create = add_parser("continuation-create", help="Create a continuation capsule.")
        continuation_create.add_argument("--project-root", required=True, help="Project root path.")
        continuation_create.add_argument("--id", required=True, help="Continuation id.")
        continuation_create.add_argument("--agent", help="Agent id.")
        continuation_create.add_argument("--session", help="Previous session id.")
        continuation_create.add_argument("--handoff", help="Handoff id.")
        continuation_create.add_argument("--expected-artifact", action="append", default=[], help="Expected artifact path. Repeatable.")
        continuation_create.add_argument("--process", help="Resume process id.")
        continuation_create.add_argument("--run", help="Resume run id.")
        continuation_create.add_argument("--assignment", help="Exact Work assignment id; creates a v2 continuation.")
        continuation_create.add_argument("--context-id", help="Exact immutable Work context id.")
        continuation_create.add_argument("--workplace", help="Workplace root override.")
        continuation_create.add_argument("--json", action="store_true", help="Print JSON.")
        continuation_create.add_argument("--stage", help="Resume stage id.")
        continuation_create.add_argument("--instruction", help="Resume instruction.")
        continuation_create.add_argument("--apply", action="store_true", help="Write the continuation capsule.")
        continuation_create.set_defaults(func=self._continuation_create)

        continuation_status = add_parser("continuation-status", help="Show continuation status.")
        continuation_status.add_argument("--project-root", required=True, help="Project root path.")
        continuation_status.add_argument("--continuation", help="Continuation id; omit to discover Work candidates without creating anything.")
        continuation_status.add_argument("--workplace", help="Workplace root override.")
        continuation_status.add_argument("--json", action="store_true", help="Print JSON.")
        continuation_status.set_defaults(func=self._continuation_status)

        continuation_resume = add_parser("continuation-resume", help="Resume verified Work, or explicitly mark a legacy wait-only record.")
        continuation_resume.add_argument("--project-root", required=True, help="Project root path.")
        continuation_resume.add_argument("--continuation", required=True, help="Continuation id.")
        continuation_resume.add_argument("--session", help="Bind selection to this session; otherwise return mandatory exact selectors.")
        continuation_resume.add_argument("--workplace", help="Workplace root override.")
        continuation_resume.add_argument("--json", action="store_true", help="Print JSON.")
        continuation_resume.set_defaults(func=self._continuation_resume)

        continuation_doctor = add_parser("continuation-doctor", help="Validate continuation capsules.")
        continuation_doctor.add_argument("--project-root", required=True, help="Project root path.")
        continuation_doctor.set_defaults(func=self._continuation_doctor)
