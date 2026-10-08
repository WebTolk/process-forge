"""Register existing CLI commands for lifecycle."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Collection


class RunCommandParser:
    """Register the existing runs command family."""

    def __init__(
        self,
        *,
        run_complete: Callable[[argparse.Namespace], int],
        run_create: Callable[[argparse.Namespace], int],
        run_doctor: Callable[[argparse.Namespace], int],
        run_list: Callable[[argparse.Namespace], int],
        run_status: Callable[[argparse.Namespace], int],
        run_summary: Callable[[argparse.Namespace], int],
        run_statuses: Collection[str],
    ) -> None:
        self._run_complete = run_complete
        self._run_create = run_create
        self._run_doctor = run_doctor
        self._run_list = run_list
        self._run_status = run_status
        self._run_summary = run_summary
        self._run_statuses = run_statuses

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        run_create = add_parser("run-create", help="Create a project run/work session.")
        run_create.add_argument("--project-root", required=True, help="Project root path.")
        run_create.add_argument("--id", required=True, help="Run id.")
        run_create.add_argument("--title", required=True, help="Run title.")
        run_create.add_argument("--process", default="task-batch-execution", help="Process definition id.")
        run_create.add_argument("--platform", help="Selected platform id for this run.")
        run_create.add_argument("--specialization", action="append", default=[], help="Selected specialization id. Repeatable.")
        run_create.add_argument("--objective", help="Run objective.")
        run_create.add_argument("--status", default="in_progress", choices=sorted(self._run_statuses), help="Initial run status.")
        run_create.add_argument("--apply", action="store_true", help="Write run files.")
        run_create.set_defaults(func=self._run_create)

        run_list = add_parser("run-list", help="List project runs.")
        run_list.add_argument("--project-root", required=True, help="Project root path.")
        run_list.set_defaults(func=self._run_list)

        run_status = add_parser("run-status", help="Show run status and task summary.")
        run_status.add_argument("--project-root", required=True, help="Project root path.")
        run_status.add_argument("--run", required=True, help="Run id.")
        run_status.set_defaults(func=self._run_status)

        run_doctor = add_parser("run-doctor", help="Validate run consistency.")
        run_doctor.add_argument("--project-root", required=True, help="Project root path.")
        run_doctor.add_argument("--run", required=True, help="Run id.")
        run_doctor.add_argument("--runtime-events", action="store_true", help="Also check private runtime event logs for this run.")
        run_doctor.set_defaults(func=self._run_doctor)

        run_summary = add_parser("run-summary", help="Create or refresh run summary and handoff.")
        run_summary.add_argument("--project-root", required=True, help="Project root path.")
        run_summary.add_argument("--run", required=True, help="Run id.")
        run_summary.add_argument("--apply", action="store_true", help="Write summary and handoff files.")
        run_summary.set_defaults(func=self._run_summary)

        run_complete = add_parser("run-complete", help="Complete a run after blocking tasks are done.")
        run_complete.add_argument("--project-root", required=True, help="Project root path.")
        run_complete.add_argument("--run", required=True, help="Run id.")
        run_complete.add_argument("--apply", action="store_true", help="Mark the run completed.")
        run_complete.set_defaults(func=self._run_complete)


class TaskCommandParser:
    """Register the existing tasks command family."""

    def __init__(
        self,
        *,
        task_complete: Callable[[argparse.Namespace], int],
        task_create: Callable[[argparse.Namespace], int],
        task_doctor: Callable[[argparse.Namespace], int],
        task_list: Callable[[argparse.Namespace], int],
        task_start: Callable[[argparse.Namespace], int],
    ) -> None:
        self._task_complete = task_complete
        self._task_create = task_create
        self._task_doctor = task_doctor
        self._task_list = task_list
        self._task_start = task_start

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        task_create = add_parser("task-create", help="Create a task assignment inside a run.")
        task_create.add_argument("--project-root", required=True, help="Project root path.")
        task_create.add_argument("--run", required=True, help="Run id.")
        task_create.add_argument("--id", required=True, help="Task id.")
        task_create.add_argument("--title", required=True, help="Task title.")
        task_create.add_argument("--process", required=True, help="Task process id.")
        task_create.add_argument("--stage", help="Declared Process Stage for this assignment; must exist in the selected Process.")
        task_create.add_argument("--platform", help="Selected platform id for this task.")
        task_create.add_argument("--specialization", action="append", default=[], help="Selected specialization id. Repeatable.")
        task_create.add_argument("--objective", help="Task objective.")
        task_create.add_argument("--order", type=int, help="Task order override.")
        task_create.add_argument("--execution-mode", choices=["read_only", "planning_only", "docs_only", "implementation", "assurance", "release_delivery"], help="Assignment execution mode.")
        task_create.add_argument("--allowed-file", action="append", default=[], help="Repository-relative writable file or simple glob. Repeatable.")
        task_create.add_argument("--allowed-glob", action="append", default=[], help="Repository-relative writable glob. Stored in allowed_files. Repeatable.")
        task_create.add_argument("--allowed-read-file", action="append", default=[], help="Repository-relative readable file. Repeatable.")
        task_create.add_argument("--read-file", action="append", default=[], help="Alias for --allowed-read-file.")
        task_create.add_argument("--context-artifact", action="append", default=[], help="Repository-relative context artifact. Repeatable.")
        task_create.add_argument("--required-source", action="append", default=[], help="Required source to include in assignment capsules. Repeatable.")
        task_create.add_argument("--workspace-knowledge-resource", action="append", default=[], help="Workplace knowledge resource id/ref granted through private runtime access. Repeatable.")
        task_create.add_argument("--workspace-template", action="append", default=[], help="Workplace template root/id granted through private runtime access. Repeatable.")
        task_create.add_argument("--workspace-tool", action="append", default=[], help="Workplace tool id granted through private runtime access. Repeatable.")
        task_create.add_argument("--workspace-mcp", action="append", default=[], help="Workplace MCP server id granted through private runtime access. Repeatable.")
        task_create.add_argument("--forbidden-file", action="append", default=[], help="Repository-relative forbidden write file or simple glob. Repeatable.")
        task_create.add_argument("--forbidden-glob", action="append", default=[], help="Repository-relative forbidden write glob. Stored in forbidden_files. Repeatable.")
        task_create.add_argument("--owner", help="Assignment owner id.")
        task_create.add_argument("--role", help="Assignment owner role.")
        task_create.add_argument("--writer", choices=["true", "false"], default="true", help="Whether the assignment owns write scope.")
        task_create.add_argument("--required-output", action="append", default=[], help="Required output id. Repeatable.")
        task_create.add_argument("--expected-report-language", help="Expected report language.")
        task_create.add_argument("--expected-report-artifact", help="Expected durable report artifact.")
        task_create.add_argument("--reasoning-effort", choices=["minimal", "low", "medium", "high"], help="Optional agent reasoning effort for shell runtime drivers.")
        task_create.add_argument("--force-with-handoff", action="store_true", help="Allow write-scope overlap and record the overlap check for orchestrator handoff.")
        task_create.add_argument("--apply", action="store_true", help="Write task files.")
        task_create.set_defaults(func=self._task_create)

        task_list = add_parser("task-list", help="List tasks in a run.")
        task_list.add_argument("--project-root", required=True, help="Project root path.")
        task_list.add_argument("--run", required=True, help="Run id.")
        task_list.set_defaults(func=self._task_list)

        task_start = add_parser("task-start", help="Mark a task assignment in progress.")
        task_start.add_argument("--project-root", required=True, help="Project root path.")
        task_start.add_argument("--task", required=True, help="Task id.")
        task_start.set_defaults(func=self._task_start)

        task_complete = add_parser("task-complete", help="Complete a task assignment and record its result.")
        task_complete.add_argument("--project-root", required=True, help="Project root path.")
        task_complete.add_argument("--task", required=True, help="Task id.")
        task_complete.add_argument("--summary", required=True, help="Task result summary.")
        task_complete.add_argument("--artifact", action="append", help="Result artifact path. May be repeated.")
        task_complete.add_argument("--waive-required-output", action="append", default=[], help="Waive a missing required output as '<id>:<reason>'. Repeatable.")
        task_complete.add_argument("--apply", action="store_true", help="Mark the task done.")
        task_complete.set_defaults(func=self._task_complete)

        task_doctor = add_parser("task-doctor", help="Validate task assignment consistency.")
        task_doctor.add_argument("--project-root", required=True, help="Project root path.")
        task_doctor.add_argument("--task", required=True, help="Task id.")
        task_doctor.set_defaults(func=self._task_doctor)


class IterationCommandParser:
    """Register the existing iterations command family."""

    def __init__(
        self,
        *,
        iteration_add: Callable[[argparse.Namespace], int],
        iteration_complete: Callable[[argparse.Namespace], int],
        iteration_kinds: Collection[str],
        iteration_statuses: Collection[str],
    ) -> None:
        self._iteration_add = iteration_add
        self._iteration_complete = iteration_complete
        self._iteration_kinds = iteration_kinds
        self._iteration_statuses = iteration_statuses

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        iteration_add = add_parser("iteration-add", help="Add a work/debug/fix/review iteration to a task.")
        iteration_add.add_argument("--project-root", required=True, help="Project root path.")
        iteration_add.add_argument("--task", required=True, help="Task id.")
        iteration_add.add_argument("--id", help="Iteration id. Defaults to the next iter-NNN value.")
        iteration_add.add_argument("--kind", required=True, choices=sorted(self._iteration_kinds), help="Iteration kind.")
        iteration_add.add_argument("--status", default="completed", choices=sorted(self._iteration_statuses), help="Iteration status.")
        iteration_add.add_argument("--summary", required=True, help="Iteration summary.")
        iteration_add.add_argument("--apply", action="store_true", help="Write the iteration.")
        iteration_add.set_defaults(func=self._iteration_add)

        iteration_complete = add_parser("iteration-complete", help="Update an existing iteration status and summary.")
        iteration_complete.add_argument("--project-root", required=True, help="Project root path.")
        iteration_complete.add_argument("--task", required=True, help="Task id.")
        iteration_complete.add_argument("--iteration", required=True, help="Iteration id.")
        iteration_complete.add_argument("--status", required=True, choices=sorted(self._iteration_statuses), help="Final iteration status.")
        iteration_complete.add_argument("--summary", help="Replacement iteration summary.")
        iteration_complete.add_argument("--apply", action="store_true", help="Write the iteration update.")
        iteration_complete.set_defaults(func=self._iteration_complete)
