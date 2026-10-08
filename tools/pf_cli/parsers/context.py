"""Register existing CLI commands for context."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class ProjectContextCommandParser:
    """Register the existing context command family."""

    def __init__(
        self,
        *,
        assignment_capsule: Callable[[argparse.Namespace], int],
        capsule_doctor: Callable[[argparse.Namespace], int],
        context_compile: Callable[[argparse.Namespace], int],
        context_resolve: Callable[[argparse.Namespace], int],
        doctor_context: Callable[[argparse.Namespace], int],
        project_context_check: Callable[[argparse.Namespace], int],
        project_context_mark_stale: Callable[[argparse.Namespace], int],
        project_context_refresh: Callable[[argparse.Namespace], int],
    ) -> None:
        self._assignment_capsule = assignment_capsule
        self._capsule_doctor = capsule_doctor
        self._context_compile = context_compile
        self._context_resolve = context_resolve
        self._doctor_context = doctor_context
        self._project_context_check = project_context_check
        self._project_context_mark_stale = project_context_mark_stale
        self._project_context_refresh = project_context_refresh

    def register_snapshot_capsule(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        project_context_refresh = add_parser("project-context-refresh", help="Refresh the project context snapshot.")
        project_context_refresh.add_argument("--project-root", required=True, help="Project root path.")
        project_context_refresh.add_argument("--workplace", help="Workplace root path; accepted for explicit lock-model workflows.")
        project_context_refresh.add_argument("--reason", default="manual", help="Refresh reason recorded in proposal/telemetry.")
        project_context_refresh.add_argument("--dry-run", action="store_true", help="Print or write a refresh proposal without updating the current snapshot.")
        project_context_refresh.add_argument("--write-proposal", help="Write dry-run proposal to this path.")
        project_context_refresh.add_argument("--apply", action="store_true", help="Accepted for command symmetry; refresh writes by default unless --dry-run is set.")
        project_context_refresh.add_argument("--force", action="store_true", help="Reserved for explicit operator override.")
        project_context_refresh.add_argument("--allow-stale", action="store_true", help="Reserved for workflows that intentionally refresh from stale context.")
        project_context_refresh.set_defaults(func=self._project_context_refresh)

        project_context_check = add_parser("project-context-check", help="Check project context snapshot freshness.")
        project_context_check.add_argument("--project-root", required=True, help="Project root path.")
        project_context_check.add_argument("--workplace", help="Workplace root path; accepted for explicit lock-model workflows.")
        project_context_check.add_argument("--json", action="store_true", help="Print machine-readable check result.")
        project_context_check.add_argument("--session-start", action="store_true", help="Evaluate policy as a session-start freshness check.")
        project_context_check.add_argument("--check-update-candidates", choices=["never", "if_due", "always"], default="if_due", help="Update-candidate check policy marker.")
        project_context_check.add_argument("--strict", action="store_true", help="Return failure unless status is fresh.")
        project_context_check.add_argument("--write-report", help="Write a Markdown context check report.")
        project_context_check.set_defaults(func=self._project_context_check)

        project_context_mark_stale = add_parser("project-context-mark-stale", help="Mark the current project context snapshot stale without refreshing it.")
        project_context_mark_stale.add_argument("--project-root", required=True, help="Project root path.")
        project_context_mark_stale.add_argument("--subject", required=True, help="Impacted subject or resource id.")
        project_context_mark_stale.add_argument("--reason", required=True, help="Stale reason.")
        project_context_mark_stale.set_defaults(func=self._project_context_mark_stale)

        assignment_capsule = add_parser("assignment-capsule", help="Create an assignment capsule from snapshot plus assignment front matter.")
        assignment_capsule.add_argument("--project-root", required=True, help="Project root path.")
        assignment_capsule.add_argument("--assignment", required=True, help="Assignment Markdown with YAML front matter or assignment YAML.")
        assignment_capsule.add_argument("--force", action="store_true", help="Overwrite an existing capsule.")
        assignment_capsule.set_defaults(func=self._assignment_capsule)

        capsule_doctor = add_parser("capsule-doctor", help="Validate that an assignment capsule pins a context snapshot.")
        capsule_doctor.add_argument("--project-root", required=True, help="Project root path.")
        capsule_doctor.add_argument("--capsule", required=True, help="Capsule YAML path.")
        capsule_doctor.set_defaults(func=self._capsule_doctor)

    def register_resolution(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        context_resolve = add_parser("context-resolve", help="Resolve project context or explicit platform/process/specialization resources.")
        context_resolve.add_argument("--project-root", required=True, help="Project root path.")
        context_resolve.add_argument("--workplace", help="Workplace root path for explicit specialization resolution.")
        context_resolve.add_argument("--platform", action="append", default=[], help="Selected platform id. Repeatable.")
        context_resolve.add_argument("--process", help="Process id.")
        context_resolve.add_argument("--specialization", action="append", default=[], help="Selected specialization id. Repeatable.")
        context_resolve.add_argument("--json", action="store_true", help="Print JSON.")
        context_resolve.set_defaults(func=self._context_resolve)

        context_compile = add_parser("context-compile", help="Deprecated compatibility Execution Context Package command.")
        context_compile.add_argument("--project-root", default=".", help="Project root path.")
        context_compile.add_argument("--assignment", required=True, help="Assignment path.")
        context_compile.add_argument("--capsule", action="store_true", help="Also write a context capsule.")
        context_compile.add_argument("--supersede", action="store_true", help="Create a versioned ECP when the default immutable ECP already exists.")
        context_compile.add_argument("--allow-requires-approval", action="store_true", help="Allow ECP creation when assignment context requires approval.")
        context_compile.set_defaults(func=self._context_compile)

        doctor_context = add_parser("doctor-context", help="Validate context resolution outputs.")
        doctor_context.add_argument("--project-root", required=True, help="Project root path.")
        doctor_context.add_argument("--assignment", help="Optional assignment path for ECP freshness check.")
        doctor_context.set_defaults(func=self._doctor_context)
