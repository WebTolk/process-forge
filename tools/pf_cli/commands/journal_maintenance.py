"""Adapt explicit operator arguments to the shared maintenance owners and JSON."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections.abc import Callable
from pathlib import Path

from processforge_core.maintenance.backup import SQLiteBackupService
from processforge_core.maintenance.contracts import (
    BackupPort,
    JournalScanPort,
    JsonObject,
    MaintenanceError,
)
from processforge_core.maintenance.journal_scan import JournalScanService
from processforge_core.maintenance.journals import JournalMaintenanceService
from processforge_core.sqlite_storage import JournalError


class JournalMaintenanceCommand:
    """Call the selected owner without transport, lifecycle or storage rules."""

    def __init__(
        self,
        *,
        backup_factory: Callable[[], BackupPort] = SQLiteBackupService,
        scan_factory: Callable[[], JournalScanPort] = JournalScanService,
        maintenance_factory: Callable[
            [], JournalMaintenanceService
        ] = JournalMaintenanceService,
    ) -> None:
        """Save narrow cold factories without constructing services or doing I/O."""
        self._backup_factory = backup_factory
        self._scan_factory = scan_factory
        self._maintenance_factory = maintenance_factory

    def execute(self, args: argparse.Namespace) -> int:
        """Print one JSON report and return 0 for success/plan or 1 for refusal.

        Expected backend/input/I/O failures become bounded error codes. Raw
        exception messages and corrupt record bytes never become CLI diagnostics.
        Explicit operator reports may contain private artifact/source locations.
        """
        operation = args.maintenance_command
        try:
            report = self._run(args)
        except MaintenanceError as error:
            report = self._failure(operation, error.code)
        except JournalError as error:
            code = str(error).partition(":")[0]
            report = self._failure(
                operation,
                code
                if re.fullmatch(r"[a-z][a-z0-9_]{0,95}", code)
                else "maintenance_journal_failed",
            )
        except OSError:
            report = self._failure(operation, "maintenance_io_failed")
        except sqlite3.Error:
            report = self._failure(operation, "maintenance_database_failed")
        except (ValueError, TypeError, KeyError, OverflowError, SystemExit):
            # The existing flow-root reader uses SystemExit for a missing
            # project manifest. Keep its private message off this JSON surface.
            report = self._failure(operation, "maintenance_input_invalid")
        try:
            if not isinstance(report, dict):
                raise TypeError("maintenance_report_not_object")
            output = json.dumps(
                report, ensure_ascii=True, sort_keys=True, allow_nan=False
            )
        except (ValueError, TypeError, OverflowError):
            report = self._failure(operation, "maintenance_report_invalid")
            output = json.dumps(report, sort_keys=True)
        print(output)
        return (
            0
            if report.get("status") in ("ok", "ready", "planned")
            and not report.get("blocked")
            and not report.get("error")
            else 1
        )

    def _run(self, args: argparse.Namespace) -> JsonObject:
        operation = args.maintenance_command
        if operation == "backup":
            return self._backup_factory().create(Path(args.database), Path(args.output))
        if operation == "verify":
            return self._backup_factory().verify(Path(args.backup))
        if operation == "restore":
            return self._backup_factory().restore(
                Path(args.backup), Path(args.destination)
            )
        if operation == "inspect":
            return self._scan_factory().preflight(
                Path(args.maintenance_project_root),
                Path(args.maintenance_workplace),
                evidence_dir=args.evidence_dir,
            )
        if operation == "import":
            return self._maintenance_factory().migrate(
                Path(args.maintenance_project_root),
                Path(args.maintenance_workplace),
                apply=args.apply,
                skip_invalid=args.skip_invalid,
                evidence_dir=args.evidence_dir,
            )
        raise MaintenanceError("maintenance_operation_invalid")

    @staticmethod
    def _failure(operation: str, code: str) -> JsonObject:
        return {"status": "failed", "operation": operation, "error": code}
