"""Register explicit local SQLite backup and legacy journal maintenance commands."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path


def register_journal_maintenance(
    add_parser: Callable[..., argparse.ArgumentParser],
    *,
    execute: Callable[[argparse.Namespace], int],
) -> None:
    """Register the maintenance group with an explicitly supplied command handler.

    Args:
        add_parser: Parent subparser registration callback.
        execute: Handler for all five operations; called only after parsing.
    """
    parser = add_parser(
        "journal-maintenance",
        help="Back up/verify/restore SQLite or inspect/import legacy journals (JSON).",
        description=(
            "Explicit local operator maintenance. Every operation returns one JSON "
            "object. Backup and restore write new files immediately; import plans "
            "until --apply. Explicit --evidence-dir may write quarantine evidence "
            "during inspect or an import plan."
        ),
        allow_abbrev=False,
    )
    operations = parser.add_subparsers(dest="maintenance_command", required=True)
    descriptions = {
        "backup": "Create and verify a new backup bundle immediately (writes files).",
        "verify": "Verify an existing backup bundle without restoring it.",
        "restore": (
            "Restore a verified backup to a new database immediately (writes files)."
        ),
        "inspect": "Check legacy journals; write quarantine only with --evidence-dir.",
        "import": "Plan a legacy journal import; mutate databases only with --apply.",
    }
    for operation, description in descriptions.items():
        command = operations.add_parser(
            operation,
            help=description,
            description=description,
            allow_abbrev=False,
        )
        command.add_argument(
            "--json", action="store_true", help="Always prints one JSON object."
        )
        if operation == "backup":
            command.add_argument("--database", type=Path, required=True)
            command.add_argument(
                "--output",
                type=Path,
                required=True,
                help="New, exclusive bundle directory.",
            )
        elif operation in ("verify", "restore"):
            command.add_argument("--backup", type=Path, required=True)
            if operation == "restore":
                command.add_argument(
                    "--destination",
                    type=Path,
                    required=True,
                    help="New database path; existing destinations are refused.",
                )
        else:
            # Keep maintenance outside eager common CLI project diagnostics.
            # Backend owners validate the unchanged explicit paths themselves.
            command.add_argument(
                "--project-root",
                dest="maintenance_project_root",
                type=Path,
                required=True,
            )
            command.add_argument(
                "--workplace", dest="maintenance_workplace", type=Path, required=True
            )
            command.add_argument(
                "--evidence-dir",
                type=Path,
                help=(
                    "Explicit quarantine directory for inspect/plans; evidence base "
                    "for an applied import. May create files even on refusal."
                ),
            )
            if operation == "import":
                command.add_argument(
                    "--apply",
                    action="store_true",
                    help="Back up existing databases, quarantine and import explicitly.",
                )
                command.add_argument(
                    "--skip-invalid",
                    action="store_true",
                    help="Explicitly permit skipping reported corrupt rows.",
                )
        command.set_defaults(func=execute)
