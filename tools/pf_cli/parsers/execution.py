"""Register existing CLI commands for execution."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class RuntimeDriverCommandParser:
    """Register the existing drivers command family."""

    def __init__(
        self,
        *,
        runtime_driver_describe: Callable[[argparse.Namespace], int],
        runtime_driver_list: Callable[[argparse.Namespace], int],
        runtime_driver_validate: Callable[[argparse.Namespace], int],
    ) -> None:
        self._runtime_driver_describe = runtime_driver_describe
        self._runtime_driver_list = runtime_driver_list
        self._runtime_driver_validate = runtime_driver_validate

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        runtime_driver = add_parser("runtime-driver", help="List, validate, or describe runtime driver manifests.")
        runtime_driver_sub = runtime_driver.add_subparsers(dest="runtime_driver_command", required=True)
        runtime_driver_list = runtime_driver_sub.add_parser("list", help="List runtime drivers.")
        runtime_driver_list.add_argument("--workplace", help="Workplace root path or workplace.yaml.")
        runtime_driver_list.add_argument("--project-root", help="Project root path for local runtime driver overrides.")
        runtime_driver_list.set_defaults(func=self._runtime_driver_list)
        runtime_driver_validate = runtime_driver_sub.add_parser("validate", help="Validate a runtime driver by id or path.")
        runtime_driver_validate.add_argument("--driver", required=True, help="Runtime driver id or manifest path.")
        runtime_driver_validate.add_argument("--workplace", help="Workplace root path or workplace.yaml.")
        runtime_driver_validate.add_argument("--project-root", help="Project root path for local runtime driver overrides.")
        runtime_driver_validate.add_argument("--executable", help="Executable override used for start-readiness checks.")
        runtime_driver_validate.set_defaults(func=self._runtime_driver_validate)
        runtime_driver_describe = runtime_driver_sub.add_parser("describe", help="Describe a runtime driver by id or path.")
        runtime_driver_describe.add_argument("--driver", required=True, help="Runtime driver id or manifest path.")
        runtime_driver_describe.add_argument("--workplace", help="Workplace root path or workplace.yaml.")
        runtime_driver_describe.add_argument("--project-root", help="Project root path for local runtime driver overrides.")
        runtime_driver_describe.set_defaults(func=self._runtime_driver_describe)

        runtime_driver_list_alias = add_parser("runtime-driver-list", help="Flat alias for runtime-driver list.")
        runtime_driver_list_alias.add_argument("--workplace", help="Workplace root path or workplace.yaml.")
        runtime_driver_list_alias.add_argument("--project-root", help="Project root path for local runtime driver overrides.")
        runtime_driver_list_alias.set_defaults(func=self._runtime_driver_list)
        runtime_driver_validate_alias = add_parser("runtime-driver-validate", help="Flat alias for runtime-driver validate.")
        runtime_driver_validate_alias.add_argument("--driver", required=True, help="Runtime driver id or manifest path.")
        runtime_driver_validate_alias.add_argument("--workplace", help="Workplace root path or workplace.yaml.")
        runtime_driver_validate_alias.add_argument("--project-root", help="Project root path for local runtime driver overrides.")
        runtime_driver_validate_alias.add_argument("--executable", help="Executable override used for start-readiness checks.")
        runtime_driver_validate_alias.set_defaults(func=self._runtime_driver_validate)
        runtime_driver_describe_alias = add_parser("runtime-driver-describe", help="Flat alias for runtime-driver describe.")
        runtime_driver_describe_alias.add_argument("--driver", required=True, help="Runtime driver id or manifest path.")
        runtime_driver_describe_alias.add_argument("--workplace", help="Workplace root path or workplace.yaml.")
        runtime_driver_describe_alias.add_argument("--project-root", help="Project root path for local runtime driver overrides.")
        runtime_driver_describe_alias.set_defaults(func=self._runtime_driver_describe)


class WorkerRunCommandParser:
    """Register the existing workers command family."""

    def __init__(
        self,
        *,
        worker_run_collect: Callable[[argparse.Namespace], int],
        worker_run_prepare: Callable[[argparse.Namespace], int],
        worker_run_start: Callable[[argparse.Namespace], int],
        worker_run_status: Callable[[argparse.Namespace], int],
        worker_run_stop: Callable[[argparse.Namespace], int],
    ) -> None:
        self._worker_run_collect = worker_run_collect
        self._worker_run_prepare = worker_run_prepare
        self._worker_run_start = worker_run_start
        self._worker_run_status = worker_run_status
        self._worker_run_stop = worker_run_stop

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        worker_run = add_parser("worker-run", help="Prepare, start, inspect, stop, or collect a worker runtime execution.")
        worker_run_sub = worker_run.add_subparsers(dest="worker_run_command", required=True)
        worker_run_prepare = worker_run_sub.add_parser("prepare", help="Create assignment capsule, launch prompt, command, and ready state.")
        worker_run_prepare.add_argument("--project-root", required=True, help="Project root path.")
        worker_run_prepare.add_argument("--task", required=True, help="Task id.")
        worker_run_prepare.add_argument("--driver", help="Runtime driver id or manifest path.")
        worker_run_prepare.add_argument("--executable", help="Executable override for generic shell drivers.")
        worker_run_prepare.add_argument("--model", help="Optional agent model for shell runtime drivers.")
        worker_run_prepare.add_argument("--reasoning-effort", choices=["minimal", "low", "medium", "high"], help="Optional agent reasoning effort for shell runtime drivers.")
        worker_run_prepare.set_defaults(func=self._worker_run_prepare)
        worker_run_start = worker_run_sub.add_parser("start", help="Start a prepared worker command and wait for completion.")
        worker_run_start.add_argument("--project-root", required=True, help="Project root path.")
        worker_run_start.add_argument("--task", required=True, help="Task id.")
        worker_run_start.add_argument("--driver", help="Runtime driver id or manifest path.")
        worker_run_start.add_argument("--executable", help="Executable override for generic shell drivers.")
        worker_run_start.add_argument("--model", help="Optional agent model for shell runtime drivers.")
        worker_run_start.add_argument("--reasoning-effort", choices=["minimal", "low", "medium", "high"], help="Optional agent reasoning effort for shell runtime drivers.")
        worker_run_start.add_argument("--detach", action="store_true", help="Start the worker process and return immediately.")
        worker_run_start.add_argument("--wait", action="store_true", help="Wait for completion. This is the default unless --detach is set.")
        worker_run_start.set_defaults(func=self._worker_run_start)
        worker_run_status = worker_run_sub.add_parser("status", help="Print worker runtime state.")
        worker_run_status.add_argument("--project-root", required=True, help="Project root path.")
        worker_run_status.add_argument("--task", required=True, help="Task id.")
        worker_run_status.set_defaults(func=self._worker_run_status)
        worker_run_stop = worker_run_sub.add_parser("stop", help="Request worker runtime stop.")
        worker_run_stop.add_argument("--project-root", required=True, help="Project root path.")
        worker_run_stop.add_argument("--task", required=True, help="Task id.")
        worker_run_stop.set_defaults(func=self._worker_run_stop)
        worker_run_collect = worker_run_sub.add_parser("collect", help="Collect worker output and complete the task when outputs exist.")
        worker_run_collect.add_argument("--project-root", required=True, help="Project root path.")
        worker_run_collect.add_argument("--task", required=True, help="Task id.")
        worker_run_collect.set_defaults(func=self._worker_run_collect)

        for alias_name, func, help_text in [
            ("worker-run-prepare", self._worker_run_prepare, "Flat alias for worker-run prepare."),
            ("worker-run-start", self._worker_run_start, "Flat alias for worker-run start."),
            ("worker-run-status", self._worker_run_status, "Flat alias for worker-run status."),
            ("worker-run-stop", self._worker_run_stop, "Flat alias for worker-run stop."),
            ("worker-run-collect", self._worker_run_collect, "Flat alias for worker-run collect."),
        ]:
            alias = add_parser(alias_name, help=help_text)
            alias.add_argument("--project-root", required=True, help="Project root path.")
            alias.add_argument("--task", required=True, help="Task id.")
            if alias_name in {"worker-run-prepare", "worker-run-start"}:
                alias.add_argument("--driver", help="Runtime driver id or manifest path.")
                alias.add_argument("--executable", help="Executable override for generic shell drivers.")
                alias.add_argument("--model", help="Optional agent model for shell runtime drivers.")
                alias.add_argument("--reasoning-effort", choices=["minimal", "low", "medium", "high"], help="Optional agent reasoning effort for shell runtime drivers.")
            alias.set_defaults(func=func)


class ExecutionInspectorCommandParser:
    """Register the existing inspector command family."""

    def __init__(
        self,
        *,
        supervisor_run: Callable[[argparse.Namespace], int],
        supervisor_status: Callable[[argparse.Namespace], int],
        supervisor_stop: Callable[[argparse.Namespace], int],
        supervisor_tick: Callable[[argparse.Namespace], int],
    ) -> None:
        self._supervisor_run = supervisor_run
        self._supervisor_status = supervisor_status
        self._supervisor_stop = supervisor_stop
        self._supervisor_tick = supervisor_tick

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        supervisor = add_parser("supervisor", help="Historical technical command for the Process Execution Inspector loop.")
        supervisor_sub = supervisor.add_subparsers(dest="supervisor_command", required=True)
        supervisor_tick = supervisor_sub.add_parser("tick", help="Run one execution-inspection pass for task runtime state.")
        supervisor_tick.add_argument("--project-root", required=True, help="Project root path.")
        supervisor_tick.add_argument("--run", help="Run id. Defaults to all active runs.")
        supervisor_tick.add_argument("--profile", help="Supervisor profile path or default.")
        supervisor_tick.add_argument("--driver", help="Runtime driver override.")
        supervisor_tick.set_defaults(func=self._supervisor_tick)
        supervisor_run = supervisor_sub.add_parser("run", help="Run a bounded execution-inspection loop.")
        supervisor_run.add_argument("--project-root", required=True, help="Project root path.")
        supervisor_run.add_argument("--run", help="Run id. Defaults to all active runs.")
        supervisor_run.add_argument("--profile", help="Supervisor profile path or default.")
        supervisor_run.add_argument("--driver", help="Runtime driver override.")
        supervisor_run.add_argument("--interval", type=float, help="Seconds between ticks.")
        supervisor_run.add_argument("--max-ticks", type=int, help="Maximum ticks before exit.")
        supervisor_run.add_argument("--final-drain-timeout", type=float, help="Maximum seconds for final observe/collect drain after the main tick loop.")
        supervisor_run.set_defaults(func=self._supervisor_run)
        supervisor_status = supervisor_sub.add_parser("status", help="Print runtime execution-inspector state.")
        supervisor_status.add_argument("--project-root", required=True, help="Project root path.")
        supervisor_status.set_defaults(func=self._supervisor_status)
        supervisor_stop = supervisor_sub.add_parser("stop", help="Write an execution-inspector stop request file.")
        supervisor_stop.add_argument("--project-root", required=True, help="Project root path.")
        supervisor_stop.set_defaults(func=self._supervisor_stop)

        supervisor_tick_alias = add_parser("supervisor-tick", help="Compatibility alias for one execution-inspection pass.")
        supervisor_tick_alias.add_argument("--project-root", required=True, help="Project root path.")
        supervisor_tick_alias.add_argument("--run", help="Run id. Defaults to all active runs.")
        supervisor_tick_alias.add_argument("--profile", help="Supervisor profile path or default.")
        supervisor_tick_alias.add_argument("--driver", help="Runtime driver override.")
        supervisor_tick_alias.set_defaults(func=self._supervisor_tick)
        supervisor_run_alias = add_parser("supervisor-run", help="Compatibility alias for a bounded execution-inspection loop.")
        supervisor_run_alias.add_argument("--project-root", required=True, help="Project root path.")
        supervisor_run_alias.add_argument("--run", help="Run id. Defaults to all active runs.")
        supervisor_run_alias.add_argument("--profile", help="Supervisor profile path or default.")
        supervisor_run_alias.add_argument("--driver", help="Runtime driver override.")
        supervisor_run_alias.add_argument("--interval", type=float, help="Seconds between ticks.")
        supervisor_run_alias.add_argument("--max-ticks", type=int, help="Maximum ticks before exit.")
        supervisor_run_alias.add_argument("--final-drain-timeout", type=float, help="Maximum seconds for final observe/collect drain after the main tick loop.")
        supervisor_run_alias.set_defaults(func=self._supervisor_run)
        supervisor_status_alias = add_parser("supervisor-status", help="Compatibility alias for runtime execution-inspector status.")
        supervisor_status_alias.add_argument("--project-root", required=True, help="Project root path.")
        supervisor_status_alias.set_defaults(func=self._supervisor_status)
        supervisor_stop_alias = add_parser("supervisor-stop", help="Compatibility alias for stopping the execution-inspector loop.")
        supervisor_stop_alias.add_argument("--project-root", required=True, help="Project root path.")
        supervisor_stop_alias.set_defaults(func=self._supervisor_stop)

        execution_inspector_tick_alias = add_parser("execution-inspector-tick", help="Thin alias for supervisor tick: one execution-inspection pass.")
        execution_inspector_tick_alias.add_argument("--project-root", required=True, help="Project root path.")
        execution_inspector_tick_alias.add_argument("--run", help="Run id. Defaults to all active runs.")
        execution_inspector_tick_alias.add_argument("--profile", help="Execution inspector profile path or default supervisor-compatible profile.")
        execution_inspector_tick_alias.add_argument("--driver", help="Runtime driver override.")
        execution_inspector_tick_alias.set_defaults(func=self._supervisor_tick)
        execution_inspector_run_alias = add_parser("execution-inspector-run", help="Thin alias for supervisor run: bounded execution-inspection loop.")
        execution_inspector_run_alias.add_argument("--project-root", required=True, help="Project root path.")
        execution_inspector_run_alias.add_argument("--run", help="Run id. Defaults to all active runs.")
        execution_inspector_run_alias.add_argument("--profile", help="Execution inspector profile path or default supervisor-compatible profile.")
        execution_inspector_run_alias.add_argument("--driver", help="Runtime driver override.")
        execution_inspector_run_alias.add_argument("--interval", type=float, help="Seconds between inspection ticks.")
        execution_inspector_run_alias.add_argument("--max-ticks", type=int, help="Maximum ticks before exit.")
        execution_inspector_run_alias.add_argument("--final-drain-timeout", type=float, help="Maximum seconds for final observe/collect drain after the main tick loop.")
        execution_inspector_run_alias.set_defaults(func=self._supervisor_run)
        execution_inspector_status_alias = add_parser("execution-inspector-status", help="Thin alias for supervisor status: runtime execution-inspector state.")
        execution_inspector_status_alias.add_argument("--project-root", required=True, help="Project root path.")
        execution_inspector_status_alias.set_defaults(func=self._supervisor_status)
        execution_inspector_stop_alias = add_parser("execution-inspector-stop", help="Thin alias for supervisor stop: request loop shutdown.")
        execution_inspector_stop_alias.add_argument("--project-root", required=True, help="Project root path.")
        execution_inspector_stop_alias.set_defaults(func=self._supervisor_stop)
