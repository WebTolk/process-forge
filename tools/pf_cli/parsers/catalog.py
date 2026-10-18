"""Register existing CLI commands for catalog."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class ProcessCatalogCommandParser:
    """Register the existing catalog command family."""

    def __init__(
        self,
        *,
        builtin_process_catalog_doctor: Callable[[argparse.Namespace], int],
        pack_activate: Callable[[argparse.Namespace], int],
        pack_list: Callable[[argparse.Namespace], int],
        process_describe: Callable[[argparse.Namespace], int],
        process_doctor: Callable[[argparse.Namespace], int],
        process_layout_doctor: Callable[[argparse.Namespace], int],
        process_layout_migrate: Callable[[argparse.Namespace], int],
        process_list: Callable[[argparse.Namespace], int],
    ) -> None:
        self._builtin_process_catalog_doctor = builtin_process_catalog_doctor
        self._pack_activate = pack_activate
        self._pack_list = pack_list
        self._process_describe = process_describe
        self._process_doctor = process_doctor
        self._process_layout_doctor = process_layout_doctor
        self._process_layout_migrate = process_layout_migrate
        self._process_list = process_list

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        process_doctor = add_parser("process-doctor", help="Validate a process definition and its generated companion files.")
        process_doctor.add_argument("--project-root", required=True, help="Project root path.")
        process_doctor.add_argument("--process", required=True, help="Process id or YAML path.")
        process_doctor.add_argument("--force", action="store_true", help="Downgrade project-mode mismatch to WARN for explicit migration/override flows.")
        process_doctor.add_argument("--contract-only", action="store_true", help="Run strict process definition contract checks in addition to project-context checks.")
        process_doctor.set_defaults(func=self._process_doctor)

        builtin_process_catalog_doctor = add_parser("builtin-process-catalog-doctor", help="Validate the built-in ProcessForge process catalog contract.")
        builtin_process_catalog_doctor.add_argument("--root", default=".", help="Repository/project root path.")
        builtin_process_catalog_doctor.add_argument("--project-root", help="Compatibility alias for --root.")
        builtin_process_catalog_doctor.add_argument("--public", action="store_true", help="Validate the public catalog surface and skip internal maintenance processes.")
        builtin_process_catalog_doctor.add_argument("--json", action="store_true", help="Print machine-readable JSON report.")
        builtin_process_catalog_doctor.add_argument("--write-report", help="Write the JSON report to this path.")
        builtin_process_catalog_doctor.set_defaults(func=self._builtin_process_catalog_doctor)

        pack_list = add_parser("pack-list", help="List bundled process packs.")
        pack_list.add_argument("--origin", choices=["official"], default="official", help="Filter by pack origin.")
        pack_list.add_argument("--available", action="store_true", help="List packs available from the distribution.")
        pack_list.add_argument("--active", action="store_true", help="List only packs active in the selected workplace.")
        pack_list.add_argument("--workplace", help="Workplace root used to resolve activation state.")
        pack_list.add_argument("--project-root", help="Project root used to resolve its linked workplace.")
        pack_list.set_defaults(func=self._pack_list)

        pack_activate = add_parser("pack-activate", help="Activate a bundled process pack in a workplace.")
        pack_activate.add_argument("--id", required=True, help="Exact process pack id.")
        pack_activate.add_argument("--workplace", required=True, help="Workplace root path.")
        pack_activate.add_argument("--apply", action="store_true", help="Write the activation registry.")
        pack_activate.set_defaults(func=self._pack_activate)

        process_list = add_parser("process-list", help="List available process definitions.")
        process_list.add_argument("--project-root", default=".", help="Project root path.")
        process_list.add_argument("--workplace", help="Workplace root override used to resolve official pack activation.")
        process_list.add_argument("--origin", choices=["kernel", "core", "official", "workspace", "project", "user", "custom", "examples", "legacy_flat"], help="Filter by process origin/root kind.")
        process_list.add_argument("--active", action="store_true", help="List only active process definitions.")
        process_list.add_argument("--available", action="store_true", help="Include bundled official processes that are available but inactive.")
        process_list.add_argument("--role", help="Filter by catalog role.")
        process_list.add_argument("--status", help="Filter by process status.")
        process_list.add_argument("--all", action="store_true", help="Include internal, hidden, and legacy-flat processes.")
        process_list.set_defaults(func=self._process_list)

        process_describe = add_parser("process-describe", help="Describe a process definition.")
        process_describe.add_argument("--project-root", required=True, help="Project root path.")
        process_describe.add_argument("--workplace", help="Workplace root override used to resolve official pack activation.")
        process_describe.add_argument("--process", required=True, help="Process id or YAML path.")
        process_describe.set_defaults(func=self._process_describe)

        process_show = add_parser("process-show", help="Show one active or available process definition.")
        process_show.add_argument("process", help="Process id or YAML path.")
        process_show.add_argument("--project-root", default=".", help="Project root path.")
        process_show.add_argument("--workplace", help="Workplace root override used to resolve official pack activation.")
        process_show.set_defaults(func=self._process_describe)

        process_layout_doctor = add_parser("process-layout-doctor", help="Validate process directory layout roots and collision policy.")
        process_layout_doctor.add_argument("--root", default=".", help="Repository/project root path.")
        process_layout_doctor.set_defaults(func=self._process_layout_doctor)

        process_layout_migrate = add_parser("process-layout-migrate", help="Move legacy flat process YAML files into root-aware process directories.")
        process_layout_migrate.add_argument("--root", default=".", help="Repository/project root path.")
        process_layout_migrate.add_argument("--custom", action="store_true", help="Move unknown legacy-flat files to processes/custom instead of processes/user.")
        process_layout_migrate.add_argument("--apply", action="store_true", help="Apply file moves. Default is dry-run.")
        process_layout_migrate.set_defaults(func=self._process_layout_migrate)
