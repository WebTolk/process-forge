"""Register existing CLI commands for project."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class ProjectCommandParser:
    """Register the existing project command family."""

    def __init__(
        self,
        *,
        doctor_project: Callable[[argparse.Namespace], int],
        init_project: Callable[[argparse.Namespace], int],
        project_init_repair: Callable[[argparse.Namespace], int],
        project_init_status: Callable[[argparse.Namespace], int],
        project_mode_doctor: Callable[[argparse.Namespace], int],
        project_mode_set: Callable[[argparse.Namespace], int],
        project_mode_status: Callable[[argparse.Namespace], int],
    ) -> None:
        self._doctor_project = doctor_project
        self._init_project = init_project
        self._project_init_repair = project_init_repair
        self._project_init_status = project_init_status
        self._project_mode_doctor = project_mode_doctor
        self._project_mode_set = project_mode_set
        self._project_mode_status = project_mode_status

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        init_project = add_parser("init-project", help="Initialize a ProcessForge project layer.")
        init_project.add_argument("--project-root", required=True, help="Project root path.")
        init_project.add_argument("--workplace", required=True, help="Path to workplace.yaml.")
        init_project.add_argument("--type", dest="project_type", help="Project type override.")
        init_project.add_argument("--coordination-mode", choices=["inherit", "simple", "organized"], help="Project coordination mode.")
        init_project.add_argument("--platform", action="append", default=[], help="Explicit platform contract id. Repeatable.")
        init_project.add_argument("--specialization", action="append", default=[], help="Explicit specialization id. Repeatable.")
        init_project.add_argument("--process", help="Explicit active process id.")
        init_project.add_argument("--answers", help="Optional project answers YAML.")
        init_project.add_argument("--entry-budget-file", help="Optional JSON array of observed generic entry budget policies.")
        init_project.add_argument("--interactive", action="store_true", help="Accepted for first-run UX; prompts are not required in file-only MVP.")
        init_project.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        init_project.add_argument("--apply", action="store_true", help="Write files.")
        init_project.add_argument("--force", action="store_true", help="Overwrite existing files.")
        init_project.add_argument("--allow-missing-workplace", action="store_true", help="Allow apply mode with a missing workplace manifest.")
        init_project.set_defaults(func=self._init_project)

        project_init = add_parser("project-init", help="Alias for init-project.")
        project_init.add_argument("--project-root", required=True, help="Project root path.")
        project_init.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        project_init.add_argument("--type", dest="project_type", help="Project type override.")
        project_init.add_argument("--coordination-mode", choices=["inherit", "simple", "organized"], help="Project coordination mode.")
        project_init.add_argument("--platform", action="append", default=[], help="Explicit platform contract id. Repeatable.")
        project_init.add_argument("--specialization", action="append", default=[], help="Explicit specialization id. Repeatable.")
        project_init.add_argument("--process", help="Explicit active process id.")
        project_init.add_argument("--answers", help="Optional project answers YAML.")
        project_init.add_argument("--entry-budget-file", help="Optional JSON array of observed generic entry budget policies.")
        project_init.add_argument("--interactive", action="store_true", help="Accepted for first-run UX; prompts are not required in file-only MVP.")
        project_init.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        project_init.add_argument("--apply", action="store_true", help="Write files.")
        project_init.add_argument("--force", action="store_true", help="Overwrite existing files.")
        project_init.add_argument("--allow-missing-workplace", action="store_true", help="Allow apply mode with a missing workplace manifest.")
        project_init.set_defaults(func=self._init_project)

        project_onboard = add_parser("project-onboard", help="Onboard a project into an existing ProcessForge workplace.")
        project_onboard.add_argument("--project-root", required=True, help="Project root path.")
        project_onboard.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        project_onboard.add_argument("--type", dest="project_type", required=True, help="Explicit project type, for example generic or fixture.project-type.a.")
        project_onboard.add_argument("--coordination-mode", choices=["inherit", "simple", "organized"], help="Project coordination mode.")
        project_onboard.add_argument("--platform", action="append", default=[], help="Explicit platform contract id. Repeatable.")
        project_onboard.add_argument("--specialization", action="append", default=[], help="Explicit specialization id. Repeatable.")
        project_onboard.add_argument("--process", help="Explicit active process id.")
        project_onboard.add_argument("--answers", help="Optional project answers YAML.")
        project_onboard.add_argument("--entry-budget-file", help="Optional JSON array of observed generic entry budget policies.")
        project_onboard.add_argument("--interactive", action="store_true", help="Accepted for first-run UX; prompts are not required in file-only MVP.")
        project_onboard.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        project_onboard.add_argument("--apply", action="store_true", help="Write files.")
        project_onboard.add_argument("--force", action="store_true", help="Overwrite existing files.")
        project_onboard.add_argument("--allow-missing-workplace", action="store_true", help="Allow apply mode with a missing workplace manifest.")
        project_onboard.set_defaults(func=self._init_project)

        project_init_status = add_parser("project-init-status", help="Read the bounded project initialization status.")
        project_init_status.add_argument("--project-root", required=True, help="Project root path.")
        project_init_status.add_argument("--workplace", help="Optional workplace root or manifest for context resolution.")
        project_init_status.add_argument("--json", action="store_true", help="Print JSON.")
        project_init_status.set_defaults(func=self._project_init_status)

        project_init_repair = add_parser("project-init-repair", help="Repair deterministic project initialization state.")
        project_init_repair.add_argument("--project-root", required=True, help="Existing PF project root path.")
        project_init_repair.add_argument("--workplace", help="Optional workplace root or manifest for context resolution.")
        project_init_repair.add_argument("--repair-action", default="refresh_context", choices=["refresh_context", "restore_deterministic_artifacts", "migrate_agent_entry", "install_codex_hooks"], help="Deterministic repair action.")
        project_init_repair.add_argument("--entry-budget-file", help="Optional JSON array of observed generic entry budget policies.")
        project_init_repair.add_argument("--reason", default="manual", help="Repair reason recorded in the event journal.")
        project_init_repair.add_argument("--apply", action="store_true", help="Perform the repair; omission is a non-mutating plan.")
        project_init_repair.set_defaults(func=self._project_init_repair)

        doctor_project = add_parser("doctor-project", help="Validate a ProcessForge project layer.")
        doctor_project.add_argument("--project-root", required=True, help="Project root path.")
        doctor_project.set_defaults(func=self._doctor_project)

        project_mode_cmd = add_parser("project-mode", help="Inspect or change project effective coordination mode.")
        project_mode_sub = project_mode_cmd.add_subparsers(dest="project_mode_command", required=True)
        project_mode_status = project_mode_sub.add_parser("status", help="Show effective project coordination mode.")
        project_mode_status.add_argument("--project-root", required=True, help="Project root path.")
        project_mode_status.add_argument("--workplace", help="Workplace root path or workplace.yaml override.")
        project_mode_status.add_argument("--json", action="store_true", help="Print JSON.")
        project_mode_status.set_defaults(func=self._project_mode_status)
        project_mode_set = project_mode_sub.add_parser("set", help="Set project coordination mode.")
        project_mode_set.add_argument("--project-root", required=True, help="Project root path.")
        project_mode_set.add_argument("--workplace", help="Workplace root path or workplace.yaml override.")
        project_mode_set.add_argument("--mode", required=True, choices=["inherit", "simple", "organized"], help="Project coordination mode.")
        project_mode_set.add_argument("--init-office", action="store_true", help="Initialize workplace Director Office when setting organized mode.")
        project_mode_set.add_argument("--json", action="store_true", help="Print JSON status after update.")
        project_mode_set.set_defaults(func=self._project_mode_set)
        project_mode_doctor = project_mode_sub.add_parser("doctor", help="Check project coordination mode.")
        project_mode_doctor.add_argument("--project-root", required=True, help="Project root path.")
        project_mode_doctor.add_argument("--workplace", help="Workplace root path or workplace.yaml override.")
        project_mode_doctor.set_defaults(func=self._project_mode_doctor)
