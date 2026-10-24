"""Worker observation inputs and the one shared detached-process registry."""

from __future__ import annotations

import csv
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..common.ids import safe_id
from ..common.json_io import json_read
from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader
from ..work.paths import WorkPaths

DETACHED_WORKER_PROCESSES: dict[tuple[str, str, str], subprocess.Popen[bytes]] = {}


def worker_process_key(
    project_root: Path, run_id: str, task_id: str
) -> tuple[str, str, str]:
    return (
        str(project_root.resolve()),
        safe_id(run_id, "run"),
        safe_id(task_id, "task"),
    )


class WorkerObservationInputService:
    def __init__(self) -> None:
        self._work_paths = WorkPaths()
        self._yaml_documents = YamlDocumentReader(fallback=_parse_simple_yaml)

    def worker_run_state_requires_reconciliation(
        self, project_root: Path, run_id: str, task_id: str, state: dict[str, Any]
    ) -> bool:
        retained = DETACHED_WORKER_PROCESSES.get(
            worker_process_key(project_root, run_id, task_id)
        )
        reference = state.get("prepared_input")
        evidence_exists = False
        if isinstance(reference, dict) and isinstance(reference.get("path"), str):
            try:
                target = (
                    project_root / reference["path"]
                ).resolve().parent / "native-tree.json"
                target.relative_to(
                    self._work_paths.worker_run(project_root, run_id, task_id)[
                        "root"
                    ].resolve()
                )
                evidence_exists = target.is_file()
            except (OSError, ValueError):
                evidence_exists = True
        if str(state.get("status") or "") != "running":
            return (
                str(state.get("status")) == "starting"
                or evidence_exists
                or retained is not None
                or (
                    isinstance(state.get("pid"), int)
                    and state.get("status")
                    in {
                        "completed",
                        "failed",
                        "timed_out",
                        "cancelled",
                        "unknown_exit",
                        "lost",
                    }
                )
            )
        paths = self._work_paths.worker_run(project_root, run_id, task_id)
        if paths["exit"].is_file():
            return True
        pid = state.get("pid")
        if not isinstance(pid, int):
            return True
        command = json_read(paths["command"])
        started_at = str(state.get("started_at") or "")
        started_dt = self.parse_runtime_timestamp(started_at)
        limits = command.get("limits")
        limits = limits if isinstance(limits, dict) else {}
        timeout_seconds = int(
            state.get("timeout_seconds") or limits.get("timeout_seconds") or 30
        )
        if started_dt and datetime.now(timezone.utc) > started_dt + timedelta(
            seconds=timeout_seconds
        ):
            return True
        proc = DETACHED_WORKER_PROCESSES.get(
            worker_process_key(project_root, run_id, task_id)
        )
        if proc is not None:
            return proc.poll() is not None
        return not self.process_pid_running(pid)

    def parse_runtime_timestamp(self, value: Any) -> datetime | None:
        if not value:
            return None
        try:
            text = str(value).replace("Z", "+00:00")
            return datetime.fromisoformat(text)
        except ValueError:
            return None

    def process_pid_running(self, pid: int) -> bool:
        if os.name == "nt":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                shell=False,
            )
            # tasklist uses a Windows console code page even when Python uses UTF-8.
            # Only the CSV PID column is relevant; localized names/messages are not.
            rows = csv.reader(
                (result.stdout or b"").decode("ascii", errors="replace").splitlines()
            )
            return any(len(row) > 1 and row[1].strip() == str(pid) for row in rows)
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    def worker_run_work_is_terminal(
        self, project_root: Path, task: dict[str, Any]
    ) -> bool:
        from processforge_core.process_execution import (
            TERMINAL_ASSIGNMENT_STATUSES,
            TERMINAL_RUN_STATUSES,
        )

        status = str(task.get("status") or "")
        if status == "cancelled" or (
            "process_execution" in task and status in TERMINAL_ASSIGNMENT_STATUSES
        ):
            return True
        run_id = safe_id(str(task.get("run_id") or "run"), "run")
        path = self._work_paths.run_root(project_root, run_id) / "run.yaml"
        run = self._yaml_documents.load(path) if path.is_file() else {}
        if "process_execution" not in task and "process_execution" not in run:
            return False
        return (
            status in TERMINAL_ASSIGNMENT_STATUSES
            or str(run.get("status") or "") in TERMINAL_RUN_STATUSES
        )
