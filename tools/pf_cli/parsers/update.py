"""Register existing CLI commands for update."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class UpdateCommandParser:
    """Register the existing updates command family."""

    def __init__(
        self,
        *,
        project_upgrade_check: Callable[[argparse.Namespace], int],
        self_update_check: Callable[[argparse.Namespace], int],
        update_apply: Callable[[argparse.Namespace], int],
        update_bootstrap_source_list: Callable[[argparse.Namespace], int],
        update_bootstrap_source_validate: Callable[[argparse.Namespace], int],
        update_candidates_clear: Callable[[argparse.Namespace], int],
        update_candidates_list: Callable[[argparse.Namespace], int],
        update_candidates_refresh: Callable[[argparse.Namespace], int],
        update_candidates_show: Callable[[argparse.Namespace], int],
        update_changelog_show: Callable[[argparse.Namespace], int],
        update_doctor: Callable[[argparse.Namespace], int],
        update_entity_sources_list: Callable[[argparse.Namespace], int],
        update_entity_sources_rebuild: Callable[[argparse.Namespace], int],
        update_manifest_validate: Callable[[argparse.Namespace], int],
        update_notifications_acknowledge: Callable[[argparse.Namespace], int],
        update_notifications_create: Callable[[argparse.Namespace], int],
        update_notifications_list: Callable[[argparse.Namespace], int],
        update_rollback: Callable[[argparse.Namespace], int],
        update_sources: Callable[[argparse.Namespace], int],
        update_stage: Callable[[argparse.Namespace], int],
        update_verify: Callable[[argparse.Namespace], int],
    ) -> None:
        self._project_upgrade_check = project_upgrade_check
        self._self_update_check = self_update_check
        self._update_apply = update_apply
        self._update_bootstrap_source_list = update_bootstrap_source_list
        self._update_bootstrap_source_validate = update_bootstrap_source_validate
        self._update_candidates_clear = update_candidates_clear
        self._update_candidates_list = update_candidates_list
        self._update_candidates_refresh = update_candidates_refresh
        self._update_candidates_show = update_candidates_show
        self._update_changelog_show = update_changelog_show
        self._update_doctor = update_doctor
        self._update_entity_sources_list = update_entity_sources_list
        self._update_entity_sources_rebuild = update_entity_sources_rebuild
        self._update_manifest_validate = update_manifest_validate
        self._update_notifications_acknowledge = update_notifications_acknowledge
        self._update_notifications_create = update_notifications_create
        self._update_notifications_list = update_notifications_list
        self._update_rollback = update_rollback
        self._update_sources = update_sources
        self._update_stage = update_stage
        self._update_verify = update_verify

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        update = add_parser("update", help="Read and validate ProcessForge update framework state.")
        update_sub = update.add_subparsers(dest="update_command", required=True)

        bootstrap_source = update_sub.add_parser("bootstrap-source", help="Read global bootstrap update sources.")
        bootstrap_source_sub = bootstrap_source.add_subparsers(dest="bootstrap_source_command", required=True)
        bootstrap_source_list = bootstrap_source_sub.add_parser("list", help="List global bootstrap update sources.")
        bootstrap_source_list.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        bootstrap_source_list.add_argument("--json", action="store_true", help="Print JSON.")
        bootstrap_source_list.set_defaults(func=self._update_bootstrap_source_list)
        bootstrap_source_validate = bootstrap_source_sub.add_parser("validate", help="Validate global bootstrap update sources.")
        bootstrap_source_validate.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        bootstrap_source_validate.set_defaults(func=self._update_bootstrap_source_validate)

        update_sources = update_sub.add_parser("sources", help="Compatibility read surface for global bootstrap update sources.")
        update_sources.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        update_sources.add_argument("--list", action="store_true", help="List global bootstrap update sources.")
        update_sources.add_argument("--validate", action="store_true", help="Validate global bootstrap update sources.")
        update_sources.add_argument("--json", action="store_true", help="Print JSON for --list.")
        update_sources.set_defaults(func=self._update_sources)

        update_sources_list = update_sub.add_parser("sources-list", help="List or validate global bootstrap update sources.")
        update_sources_list.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        update_sources_list.add_argument("--validate", action="store_true", help="Validate global bootstrap update sources before listing.")
        update_sources_list.add_argument("--json", action="store_true", help="Print JSON.")
        update_sources_list.set_defaults(func=self._update_sources, list=True)

        entity_sources = update_sub.add_parser("entity-sources", help="Read derived installed entity update sources.")
        entity_sources_sub = entity_sources.add_subparsers(dest="entity_sources_command", required=True)
        entity_sources_rebuild = entity_sources_sub.add_parser("rebuild", help="Rebuild derived entity update sources from installed manifests.")
        entity_sources_rebuild.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        entity_sources_rebuild.add_argument("--dry-run", action="store_true", help="Print derived registry without writing runtime state.")
        entity_sources_rebuild.set_defaults(func=self._update_entity_sources_rebuild)
        entity_sources_list = entity_sources_sub.add_parser("list", help="List derived entity update sources.")
        entity_sources_list.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        entity_sources_list.add_argument("--subject-type", default="all", help="Subject type filter or all.")
        entity_sources_list.add_argument("--json", action="store_true", help="Print JSON.")
        entity_sources_list.set_defaults(func=self._update_entity_sources_list)

        update_candidates = update_sub.add_parser("candidates", help="Manage update candidate cache.")
        update_candidates_sub = update_candidates.add_subparsers(dest="update_candidates_command", required=True)
        update_candidates_refresh = update_candidates_sub.add_parser("refresh", help="Fetch update manifests and refresh candidates.")
        update_candidates_refresh.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        update_candidates_refresh.add_argument("--channel", default="stable", help="Update channel.")
        update_candidates_refresh.add_argument("--dry-run", action="store_true", help="Print candidates without writing runtime state.")
        update_candidates_refresh.set_defaults(func=self._update_candidates_refresh)
        update_candidates_list = update_candidates_sub.add_parser("list", help="List cached update candidates.")
        update_candidates_list.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        update_candidates_list.add_argument("--json", action="store_true", help="Print JSON.")
        update_candidates_list.set_defaults(func=self._update_candidates_list)
        update_candidates_show = update_candidates_sub.add_parser("show", help="Show one cached update candidate as JSON.")
        update_candidates_show.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        update_candidates_show.add_argument("--candidate", required=True, help="Candidate id.")
        update_candidates_show.set_defaults(func=self._update_candidates_show)
        update_candidates_clear = update_candidates_sub.add_parser("clear", help="Clear candidate and notification caches.")
        update_candidates_clear.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        update_candidates_clear.add_argument("--dry-run", action="store_true", help="Report what would be cleared.")
        update_candidates_clear.set_defaults(func=self._update_candidates_clear)

        update_changelog = update_sub.add_parser("changelog", help="Show candidate changelog pointers or local content.")
        update_changelog_sub = update_changelog.add_subparsers(dest="update_changelog_command", required=True)
        update_changelog_show = update_changelog_sub.add_parser("show", help="Show candidate changelog.")
        update_changelog_show.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        update_changelog_show.add_argument("--candidate", required=True, help="Candidate id.")
        update_changelog_show.set_defaults(func=self._update_changelog_show)

        update_notifications = update_sub.add_parser("notifications", help="Manage update notifications.")
        update_notifications_sub = update_notifications.add_subparsers(dest="update_notifications_command", required=True)
        update_notifications_create = update_notifications_sub.add_parser("create", help="Create notifications from cached candidates.")
        update_notifications_create.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        update_notifications_create.set_defaults(func=self._update_notifications_create)
        update_notifications_list = update_notifications_sub.add_parser("list", help="List update notifications.")
        update_notifications_list.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        update_notifications_list.add_argument("--json", action="store_true", help="Print JSON.")
        update_notifications_list.set_defaults(func=self._update_notifications_list)
        update_notifications_ack = update_notifications_sub.add_parser("acknowledge", help="Acknowledge one update notification.")
        update_notifications_ack.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        update_notifications_ack.add_argument("--notification", required=True, help="Notification id.")
        update_notifications_ack.set_defaults(func=self._update_notifications_acknowledge)

        update_stage = update_sub.add_parser("stage", help="Stage an installable update candidate.")
        update_stage.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        update_stage.add_argument("--candidate", required=True, help="Candidate id.")
        update_stage.add_argument("--dry-run", action="store_true", help="Report staging target without copying.")
        update_stage.set_defaults(func=self._update_stage)
        update_verify = update_sub.add_parser("verify", help="Verify a staged update candidate.")
        update_verify.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        update_verify.add_argument("--candidate", required=True, help="Candidate id.")
        update_verify.set_defaults(func=self._update_verify)
        update_apply = update_sub.add_parser("apply", help="Apply a staged update candidate.")
        update_apply.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        update_apply.add_argument("--candidate", required=True, help="Candidate id.")
        update_apply.add_argument("--confirm", action="store_true", help="Required confirmation for apply.")
        update_apply.add_argument("--dry-run", action="store_true", help="Report apply target without writing.")
        update_apply.add_argument("--allow-custom-command", action="store_true", help="Acknowledge custom command policy; commands are not executed by default.")
        update_apply.set_defaults(func=self._update_apply)
        update_rollback = update_sub.add_parser("rollback", help="Rollback an applied update candidate from backup.")
        update_rollback.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        update_rollback.add_argument("--candidate", required=True, help="Candidate id.")
        update_rollback.set_defaults(func=self._update_rollback)
        update_doctor = update_sub.add_parser("doctor", help="Validate update runtime caches.")
        update_doctor.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        update_doctor.set_defaults(func=self._update_doctor)

        update_manifest = update_sub.add_parser("manifest", help="Validate normalized update manifest fixtures.")
        update_manifest_sub = update_manifest.add_subparsers(dest="update_manifest_command", required=True)
        update_manifest_validate = update_manifest_sub.add_parser("validate", help="Validate a normalized update manifest fixture.")
        update_manifest_validate.add_argument("--file", required=True, help="JSON or YAML normalized update manifest.")
        update_manifest_validate.set_defaults(func=self._update_manifest_validate)

        self_update = add_parser("self-update-check", help="Check the current ProcessForge distribution update index.")
        self_update.add_argument("--distribution-root", help="ProcessForge distribution root. Defaults to this checkout.")
        self_update.add_argument("--current-version", help="Current ProcessForge version to compare.")
        self_update.add_argument("--channel", default="stable", help="Update channel.")
        self_update.set_defaults(func=self._self_update_check)

        project_upgrade = add_parser("project-upgrade-check", help="Write a project update assessment without modifying project files.")
        project_upgrade.add_argument("--project-root", required=True, help="Project root path.")
        project_upgrade.add_argument("--current-version", help="Current ProcessForge version override.")
        project_upgrade.add_argument("--channel", default="stable", help="Update channel.")
        project_upgrade.set_defaults(func=self._project_upgrade_check)
