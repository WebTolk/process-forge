"""Register existing CLI commands for workplace."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class WorkplaceCommandParser:
    """Register the existing workplace command family."""

    def __init__(
        self,
        *,
        doctor_workplace: Callable[[argparse.Namespace], int],
        first_run: Callable[[argparse.Namespace], int],
        init_workplace: Callable[[argparse.Namespace], int],
        workplace_mode_doctor: Callable[[argparse.Namespace], int],
        workplace_mode_set: Callable[[argparse.Namespace], int],
        workplace_mode_set_default_project_mode: Callable[[argparse.Namespace], int],
        workplace_mode_status: Callable[[argparse.Namespace], int],
        workplace_setup_apply: Callable[[argparse.Namespace], int],
        workplace_setup_review: Callable[[argparse.Namespace], int],
        workplace_setup_start: Callable[[argparse.Namespace], int],
        workplace_setup_status: Callable[[argparse.Namespace], int],
    ) -> None:
        self._doctor_workplace = doctor_workplace
        self._first_run = first_run
        self._init_workplace = init_workplace
        self._workplace_mode_doctor = workplace_mode_doctor
        self._workplace_mode_set = workplace_mode_set
        self._workplace_mode_set_default_project_mode = workplace_mode_set_default_project_mode
        self._workplace_mode_status = workplace_mode_status
        self._workplace_setup_apply = workplace_setup_apply
        self._workplace_setup_review = workplace_setup_review
        self._workplace_setup_start = workplace_setup_start
        self._workplace_setup_status = workplace_setup_status

    def register_setup(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        init_workplace = add_parser("init-workplace", help="Initialize a ProcessForge workplace layer.")
        init_workplace.add_argument("--root", required=True, help="Workplace root path.")
        init_workplace.add_argument("--answers", help="Optional workplace answers YAML.")
        init_workplace.add_argument("--profile", help="Opaque workplace profile id used to select bundled process packs from manifest data.")
        init_workplace.add_argument("--interactive", action="store_true", help="Accepted for first-run UX; prompts are not required in file-only MVP.")
        init_workplace.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        init_workplace.add_argument("--apply", action="store_true", help="Write files.")
        init_workplace.add_argument("--force", action="store_true", help="Overwrite existing files.")
        init_workplace.set_defaults(func=self._init_workplace)

        workplace_init = add_parser("workplace-init", help="First-run alias for init-workplace.")
        workplace_init.add_argument("--workplace", dest="root", required=True, help="Workplace root path.")
        workplace_init.add_argument("--answers", help="Optional workplace answers YAML.")
        workplace_init.add_argument("--profile", help="Opaque workplace profile id used to select bundled process packs from manifest data.")
        workplace_init.add_argument("--interactive", action="store_true", help="Accepted for first-run UX; prompts are not required in file-only MVP.")
        workplace_init.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        workplace_init.add_argument("--apply", action="store_true", help="Write files.")
        workplace_init.add_argument("--force", action="store_true", help="Overwrite existing files.")
        workplace_init.set_defaults(func=self._init_workplace)

        workplace_setup = add_parser("workplace-setup", help="Agent-guided workplace setup workflow.")
        workplace_setup_sub = workplace_setup.add_subparsers(dest="workplace_setup_command", required=True)
        workplace_setup_start = workplace_setup_sub.add_parser("start", help="Start a guided workplace setup session.")
        workplace_setup_start.add_argument("--workplace", required=True, help="Workplace root path.")
        workplace_setup_start.add_argument("--answers", help="Optional guided setup answers YAML.")
        workplace_setup_start.add_argument("--session-id", default="default", help="Setup session id.")
        workplace_setup_start.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        workplace_setup_start.add_argument("--apply", action="store_true", help="Write setup session files.")
        workplace_setup_start.set_defaults(func=self._workplace_setup_start)
        workplace_setup_review = workplace_setup_sub.add_parser("review", help="Review guided workplace setup answers and proposal.")
        workplace_setup_review.add_argument("--workplace", required=True, help="Workplace root path.")
        workplace_setup_review.add_argument("--answers", help="Optional guided setup answers YAML.")
        workplace_setup_review.add_argument("--session-id", default="default", help="Setup session id.")
        workplace_setup_review.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        workplace_setup_review.add_argument("--apply", action="store_true", help="Accepted for command symmetry; review writes unless --dry-run is used.")
        workplace_setup_review.set_defaults(func=self._workplace_setup_review)
        workplace_setup_apply = workplace_setup_sub.add_parser("apply", help="Apply a guided workplace setup proposal.")
        workplace_setup_apply.add_argument("--workplace", required=True, help="Workplace root path.")
        workplace_setup_apply.add_argument("--answers", help="Optional guided setup answers YAML.")
        workplace_setup_apply.add_argument("--session-id", default="default", help="Setup session id.")
        workplace_setup_apply.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        workplace_setup_apply.add_argument("--apply", action="store_true", help="Write workplace files.")
        workplace_setup_apply.set_defaults(func=self._workplace_setup_apply)
        workplace_setup_status = workplace_setup_sub.add_parser("status", help="Show guided workplace setup session status.")
        workplace_setup_status.add_argument("--workplace", required=True, help="Workplace root path.")
        workplace_setup_status.add_argument("--answers", help="Accepted for namespace compatibility.")
        workplace_setup_status.add_argument("--session-id", default="default", help="Setup session id.")
        workplace_setup_status.add_argument("--dry-run", action="store_true", help="Accepted for namespace compatibility.")
        workplace_setup_status.add_argument("--apply", action="store_true", help="Accepted for namespace compatibility.")
        workplace_setup_status.set_defaults(func=self._workplace_setup_status)

    def register_modes(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        doctor_workplace = add_parser("doctor-workplace", help="Validate a ProcessForge workplace layer.")
        doctor_workplace.add_argument("--root", required=True, help="Workplace root path.")
        doctor_workplace.set_defaults(func=self._doctor_workplace)

        workplace_mode = add_parser("workplace-mode", help="Inspect or change workplace coordination mode.")
        workplace_mode_sub = workplace_mode.add_subparsers(dest="workplace_mode_command", required=True)
        workplace_mode_status = workplace_mode_sub.add_parser("status", help="Show workplace coordination mode.")
        workplace_mode_status.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        workplace_mode_status.add_argument("--json", action="store_true", help="Print JSON.")
        workplace_mode_status.set_defaults(func=self._workplace_mode_status)
        workplace_mode_set = workplace_mode_sub.add_parser("set", help="Set workplace Director capability flags.")
        workplace_mode_set.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        workplace_mode_set.add_argument("--director-enabled", choices=["true", "false"], help="Enable or disable Director capability.")
        workplace_mode_set.add_argument("--director-office-enabled", choices=["true", "false"], help="Enable or disable Director Office initialization.")
        workplace_mode_set.add_argument("--force", action="store_true", help="Allow disabling Director despite active organized sessions.")
        workplace_mode_set.add_argument("--json", action="store_true", help="Print JSON status after update.")
        workplace_mode_set.set_defaults(func=self._workplace_mode_set)
        workplace_mode_default = workplace_mode_sub.add_parser("set-default-project-mode", help="Set workplace default mode for inherit projects.")
        workplace_mode_default.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        workplace_mode_default.add_argument("--mode", required=True, choices=["simple", "organized"], help="Default mode for projects with coordination.mode=inherit.")
        workplace_mode_default.add_argument("--json", action="store_true", help="Print JSON status after update.")
        workplace_mode_default.set_defaults(func=self._workplace_mode_set_default_project_mode)
        workplace_mode_doctor = workplace_mode_sub.add_parser("doctor", help="Check workplace coordination mode.")
        workplace_mode_doctor.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        workplace_mode_doctor.set_defaults(func=self._workplace_mode_doctor)

    def register_first_run(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        first_run = add_parser("first-run", help="Convenience command that runs workplace-init and then project-onboard.")
        first_run.add_argument("--workplace", required=True, help="Workplace root path.")
        first_run.add_argument("--project-root", required=True, help="Project root path.")
        first_run.add_argument("--type", dest="project_type", required=True, help="Project type.")
        first_run.add_argument("--interactive", action="store_true", help="Accepted for first-run UX; prompts are not required in file-only MVP.")
        first_run.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        first_run.add_argument("--apply", action="store_true", help="Write files.")
        first_run.add_argument("--force", action="store_true", help="Overwrite existing files.")
        first_run.set_defaults(func=self._first_run)
