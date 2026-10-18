"""Register existing CLI commands for runtime."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class RuntimeCommandParser:
    """Register the existing runtime command family."""

    def __init__(
        self,
        *,
        runtime_autostart_install: Callable[[argparse.Namespace], int],
        runtime_autostart_remove: Callable[[argparse.Namespace], int],
        runtime_autostart_status: Callable[[argparse.Namespace], int],
        runtime_doctor: Callable[[argparse.Namespace], int],
        runtime_event: Callable[[argparse.Namespace], int],
        runtime_project_state: Callable[[argparse.Namespace], int],
        runtime_resolve: Callable[[argparse.Namespace], int],
        runtime_restart: Callable[[argparse.Namespace], int],
        runtime_serve: Callable[[argparse.Namespace], int],
        runtime_session_register: Callable[[argparse.Namespace], int],
        runtime_start: Callable[[argparse.Namespace], int],
        runtime_status: Callable[[argparse.Namespace], int],
        runtime_stop: Callable[[argparse.Namespace], int],
        runtime_tick: Callable[[argparse.Namespace], int],
        runtime_work_state: Callable[[argparse.Namespace], int],
    ) -> None:
        self._runtime_autostart_install = runtime_autostart_install
        self._runtime_autostart_remove = runtime_autostart_remove
        self._runtime_autostart_status = runtime_autostart_status
        self._runtime_doctor = runtime_doctor
        self._runtime_event = runtime_event
        self._runtime_project_state = runtime_project_state
        self._runtime_resolve = runtime_resolve
        self._runtime_restart = runtime_restart
        self._runtime_serve = runtime_serve
        self._runtime_session_register = runtime_session_register
        self._runtime_start = runtime_start
        self._runtime_status = runtime_status
        self._runtime_stop = runtime_stop
        self._runtime_tick = runtime_tick
        self._runtime_work_state = runtime_work_state

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        runtime = add_parser("runtime", aliases=["server"], help="Run and control the long-lived local PF Runtime process.")
        runtime_sub = runtime.add_subparsers(dest="runtime_command", required=True)

        runtime_serve = runtime_sub.add_parser("serve", aliases=["run"], help="Run PF Runtime in the foreground for one workplace.")
        runtime_serve.add_argument("--console", action="store_true", help="Show a foreground banner on an interactive terminal.")
        runtime_serve.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        runtime_serve.add_argument("--port", type=int, default=0, help="Loopback TCP port, or 0 for an ephemeral port.")
        runtime_serve.add_argument("--interval", type=float, default=2.0, help="Scheduler tick interval in seconds.")
        runtime_serve.set_defaults(func=self._runtime_serve)

        runtime_start = runtime_sub.add_parser("start", help="Start PF Runtime in the background for one workplace.")
        runtime_start.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        runtime_start.add_argument("--port", type=int, default=0, help="Loopback TCP port, or 0 for an ephemeral port.")
        runtime_start.add_argument("--interval", type=float, default=2.0, help="Scheduler tick interval in seconds.")
        runtime_start.add_argument("--timeout", type=float, default=10.0, help="Seconds to wait for readiness.")
        runtime_start.add_argument("--json", action="store_true", help="Print JSON.")
        runtime_start.set_defaults(func=self._runtime_start)

        runtime_stop = runtime_sub.add_parser("stop", help="Stop PF Runtime for one workplace.")
        runtime_stop.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        runtime_stop.add_argument("--timeout", type=float, default=10.0, help="Seconds to wait for graceful shutdown.")
        runtime_stop.set_defaults(func=self._runtime_stop)
        runtime_stop.add_argument("--force", action="store_true", help="Explicitly bypass the server busy guard.")

        runtime_restart = runtime_sub.add_parser("restart", help="Restart PF Runtime for one workplace.")
        runtime_restart.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        runtime_restart.add_argument("--port", type=int, default=0, help="Loopback TCP port, or 0 for an ephemeral port.")
        runtime_restart.add_argument("--interval", type=float, default=2.0, help="Scheduler tick interval in seconds.")
        runtime_restart.add_argument("--timeout", type=float, default=10.0, help="Seconds to wait for stop/start.")
        runtime_restart.add_argument("--json", action="store_true", help="Print JSON.")
        runtime_restart.set_defaults(func=self._runtime_restart)
        runtime_restart.add_argument("--force", action="store_true", help="Explicitly bypass the server busy guard.")

        runtime_status = runtime_sub.add_parser("status", help="Print PF Runtime process and projection status.")
        runtime_status.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        runtime_status.add_argument("--json", action="store_true", help="Print JSON.")
        runtime_status.set_defaults(func=self._runtime_status)

        runtime_doctor = runtime_sub.add_parser("doctor", help="Check PF Runtime state, singleton, auth, and protocol compatibility.")
        runtime_doctor.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        runtime_doctor.set_defaults(func=self._runtime_doctor)

        runtime_event = runtime_sub.add_parser("event", help="Send one normalized agent event through the long-lived runtime.")
        runtime_event.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        runtime_event.add_argument("--project-root", help="Project root path override.")
        runtime_event.add_argument("--input", default="-", help="JSON input path or '-' for stdin.")
        runtime_event.add_argument("--json", action="store_true", help="Print JSON.")
        runtime_event.set_defaults(func=self._runtime_event)

        runtime_session = runtime_sub.add_parser("session-register", help="Bind a Codex/runtime session id to one project.")
        runtime_session.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        runtime_session.add_argument("--session", required=True, help="Runtime/agent session id.")
        runtime_session.add_argument("--agent", help="Agent id.")
        runtime_session.add_argument("--project-root", help="Project root path.")
        runtime_session.add_argument("--cwd", help="Working directory fallback used by hook adapters.")
        runtime_session.add_argument("--json", action="store_true", help="Print JSON.")
        runtime_session.set_defaults(func=self._runtime_session_register)

        runtime_project_state = runtime_sub.add_parser("project-state", help="Read project state for a routed Runtime session.")
        runtime_project_state.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        runtime_project_state.add_argument("--session", help="Runtime/agent session id.")
        runtime_project_state.add_argument("--project-root", help="Project root path fallback.")
        runtime_project_state.add_argument("--json", action="store_true", help="Print JSON.")
        runtime_project_state.set_defaults(func=self._runtime_project_state)

        runtime_work_state = runtime_sub.add_parser("work-state", help="Read current work state for a routed Runtime session.")
        runtime_work_state.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        runtime_work_state.add_argument("--session", help="Runtime/agent session id.")
        runtime_work_state.add_argument("--project-root", help="Project root path fallback.")
        runtime_work_state.add_argument("--json", action="store_true", help="Print JSON.")
        runtime_work_state.set_defaults(func=self._runtime_work_state)

        runtime_resolve = runtime_sub.add_parser("resolve", help="Resolve the project handle for a Runtime session.")
        runtime_resolve.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        runtime_resolve.add_argument("--session", help="Runtime/agent session id.")
        runtime_resolve.add_argument("--project-root", help="Project root path fallback.")
        runtime_resolve.add_argument("--resource", help="Resolved knowledge resource id.")
        runtime_resolve.add_argument("--json", action="store_true", help="Print JSON.")
        runtime_resolve.set_defaults(func=self._runtime_resolve)

        runtime_tick = runtime_sub.add_parser("tick", help="Request one Runtime scheduler pass for known or explicit projects.")
        runtime_tick.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        runtime_tick.add_argument("--project-root", action="append", default=[], help="Project root path. Repeatable.")
        runtime_tick.add_argument("--director", action="store_true", help="Run hosted Agent Director tick for organized projects.")
        runtime_tick.add_argument("--inspector", action="store_true", help="Run hosted Execution Inspector tick.")
        runtime_tick.add_argument("--json", action="store_true", help="Print JSON.")
        runtime_tick.set_defaults(func=self._runtime_tick)

        runtime_autostart = runtime_sub.add_parser("autostart", help="Manage Windows Task Scheduler autostart for PF Runtime.")
        runtime_autostart_sub = runtime_autostart.add_subparsers(dest="runtime_autostart_command", required=True)

        def add_runtime_autostart_common(parser: argparse.ArgumentParser) -> None:
            parser.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
            parser.add_argument("--distribution-root", help="Installed ProcessForge distribution root. Defaults to this CLI distribution.")
            parser.add_argument("--python", help="Python executable stored in the scheduled task. Defaults to the current interpreter.")
            parser.add_argument("--port", type=int, default=0, help="Runtime loopback port, or 0 for an ephemeral port.")
            parser.add_argument("--interval", type=float, default=2.0, help="Runtime scheduler tick interval in seconds.")
            parser.add_argument("--json", action="store_true", help="Print JSON.")

        runtime_autostart_status = runtime_autostart_sub.add_parser("status", help="Inspect the workplace Runtime scheduled task.")
        add_runtime_autostart_common(runtime_autostart_status)
        runtime_autostart_status.set_defaults(func=self._runtime_autostart_status)
        runtime_autostart_install = runtime_autostart_sub.add_parser("install", help="Plan or install the workplace Runtime scheduled task.")
        add_runtime_autostart_common(runtime_autostart_install)
        runtime_autostart_install.add_argument("--delay-seconds", type=int, default=10, help="Delay after interactive logon.")
        runtime_autostart_install.add_argument("--replace", action="store_true", help="Replace a drifted task with the deterministic ProcessForge definition.")
        runtime_autostart_install.add_argument("--apply", action="store_true", help="Create the task; otherwise show a dry run.")
        runtime_autostart_install.set_defaults(func=self._runtime_autostart_install)
        runtime_autostart_remove = runtime_autostart_sub.add_parser("remove", help="Plan or remove the workplace Runtime scheduled task.")
        add_runtime_autostart_common(runtime_autostart_remove)
        runtime_autostart_remove.add_argument("--force", action="store_true", help="Remove a drifted task with the deterministic ProcessForge name.")
        runtime_autostart_remove.add_argument("--apply", action="store_true", help="Delete the task; otherwise show a dry run.")
        runtime_autostart_remove.set_defaults(func=self._runtime_autostart_remove)
