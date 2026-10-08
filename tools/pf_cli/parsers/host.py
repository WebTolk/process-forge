"""Register existing CLI commands for host."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class CodexMcpCommandParser:
    """Register the existing codex mcp command family."""

    def __init__(
        self,
        *,
        codex_mcp_install: Callable[[argparse.Namespace], int],
        codex_mcp_remove: Callable[[argparse.Namespace], int],
        codex_mcp_status: Callable[[argparse.Namespace], int],
    ) -> None:
        self._codex_mcp_install = codex_mcp_install
        self._codex_mcp_remove = codex_mcp_remove
        self._codex_mcp_status = codex_mcp_status

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        codex_mcp = add_parser("codex-mcp", help="Manage the host-owned ProcessForge stdio MCP registration in Codex.")
        codex_mcp_sub = codex_mcp.add_subparsers(dest="codex_mcp_command", required=True)

        def add_codex_mcp_common(parser: argparse.ArgumentParser) -> None:
            parser.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
            parser.add_argument("--distribution-root", help="Installed ProcessForge distribution root. Defaults to this CLI distribution.")
            parser.add_argument("--name", default="processforge", help="Codex MCP server name.")
            parser.add_argument("--python", help="Python command used by Codex. Defaults to the current interpreter.")
            parser.add_argument("--codex", help="Codex executable. Defaults to the executable on PATH.")
            parser.add_argument("--json", action="store_true", help="Print JSON.")

        codex_mcp_status = codex_mcp_sub.add_parser("status", help="Inspect the Codex ProcessForge MCP registration.")
        add_codex_mcp_common(codex_mcp_status)
        codex_mcp_status.set_defaults(func=self._codex_mcp_status)
        codex_mcp_install = codex_mcp_sub.add_parser("install", help="Plan or install the Codex ProcessForge MCP registration.")
        add_codex_mcp_common(codex_mcp_install)
        codex_mcp_install.add_argument("--replace", action="store_true", help="Replace a drifted registration.")
        codex_mcp_install.add_argument("--apply", action="store_true", help="Write Codex configuration; otherwise show a dry run.")
        codex_mcp_install.set_defaults(func=self._codex_mcp_install)
        codex_mcp_remove = codex_mcp_sub.add_parser("remove", help="Plan or remove the Codex ProcessForge MCP registration.")
        add_codex_mcp_common(codex_mcp_remove)
        codex_mcp_remove.add_argument("--force", action="store_true", help="Remove a drifted registration with this name.")
        codex_mcp_remove.add_argument("--apply", action="store_true", help="Write Codex configuration; otherwise show a dry run.")
        codex_mcp_remove.set_defaults(func=self._codex_mcp_remove)


class RuntimeHostCommandParser:
    """Register the existing runtime host command family."""

    def __init__(
        self,
        *,
        runtime_host_event: Callable[[argparse.Namespace], int],
        runtime_host_init: Callable[[argparse.Namespace], int],
        runtime_host_project_state: Callable[[argparse.Namespace], int],
        runtime_host_projection_doctor: Callable[[argparse.Namespace], int],
        runtime_host_rebuild_projections: Callable[[argparse.Namespace], int],
        runtime_host_resolve: Callable[[argparse.Namespace], int],
        runtime_host_status: Callable[[argparse.Namespace], int],
        runtime_host_tick: Callable[[argparse.Namespace], int],
        runtime_host_work_state: Callable[[argparse.Namespace], int],
    ) -> None:
        self._runtime_host_event = runtime_host_event
        self._runtime_host_init = runtime_host_init
        self._runtime_host_project_state = runtime_host_project_state
        self._runtime_host_projection_doctor = runtime_host_projection_doctor
        self._runtime_host_rebuild_projections = runtime_host_rebuild_projections
        self._runtime_host_resolve = runtime_host_resolve
        self._runtime_host_status = runtime_host_status
        self._runtime_host_tick = runtime_host_tick
        self._runtime_host_work_state = runtime_host_work_state

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        runtime_host = add_parser("runtime-host", help="Host existing PF Core runtime passes through a lazy local Runtime PoC.")
        runtime_host_sub = runtime_host.add_subparsers(dest="runtime_host_command", required=True)

        runtime_host_init = runtime_host_sub.add_parser("init", help="Initialize or refresh Runtime project handles.")
        runtime_host_init.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        runtime_host_init.add_argument("--project-root", action="append", default=[], help="Project root path. Repeatable.")
        runtime_host_init.set_defaults(func=self._runtime_host_init)

        runtime_host_event = runtime_host_sub.add_parser("event", help="Accept one normalized agent event and append a PF event envelope.")
        runtime_host_event.add_argument("--workplace", help="Workplace root path or workplace.yaml.")
        runtime_host_event.add_argument("--project-root", help="Project root path override.")
        runtime_host_event.add_argument("--input", default="-", help="JSON input path or '-' for stdin.")
        runtime_host_event.add_argument("--json", action="store_true", help="Print JSON.")
        runtime_host_event.set_defaults(func=self._runtime_host_event)

        runtime_host_status = runtime_host_sub.add_parser("status", help="Print Runtime host status.")
        runtime_host_status.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        runtime_host_status.add_argument("--project-root", action="append", default=[], help="Project root path. Repeatable.")
        runtime_host_status.add_argument("--json", action="store_true", help="Print JSON.")
        runtime_host_status.set_defaults(func=self._runtime_host_status)

        runtime_host_project_state = runtime_host_sub.add_parser("project-state", help="MCP-like read-only project state for a routed Runtime session.")
        runtime_host_project_state.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        runtime_host_project_state.add_argument("--session", help="Runtime/agent session id.")
        runtime_host_project_state.add_argument("--project-root", help="Project root path fallback.")
        runtime_host_project_state.add_argument("--json", action="store_true", help="Print JSON.")
        runtime_host_project_state.set_defaults(func=self._runtime_host_project_state)

        runtime_host_work_state = runtime_host_sub.add_parser("work-state", help="MCP-like read-only work state for a routed Runtime session.")
        runtime_host_work_state.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        runtime_host_work_state.add_argument("--session", help="Runtime/agent session id.")
        runtime_host_work_state.add_argument("--project-root", help="Project root path fallback.")
        runtime_host_work_state.add_argument("--json", action="store_true", help="Print JSON.")
        runtime_host_work_state.set_defaults(func=self._runtime_host_work_state)

        runtime_host_resolve = runtime_host_sub.add_parser("resolve", help="Resolve the project handle for a Runtime session.")
        runtime_host_resolve.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        runtime_host_resolve.add_argument("--session", help="Runtime/agent session id.")
        runtime_host_resolve.add_argument("--project-root", help="Project root path fallback.")
        runtime_host_resolve.add_argument("--json", action="store_true", help="Print JSON.")
        runtime_host_resolve.set_defaults(func=self._runtime_host_resolve)

        runtime_host_tick = runtime_host_sub.add_parser("tick", help="Run hosted Ledger maintenance plus optional Director/Inspector ticks.")
        runtime_host_tick.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
        runtime_host_tick.add_argument("--project-root", action="append", default=[], help="Project root path. Repeatable.")
        runtime_host_tick.add_argument("--director", action="store_true", help="Host existing agent-director-tick for organized projects.")
        runtime_host_tick.add_argument("--inspector", action="store_true", help="Host existing execution inspector tick.")
        runtime_host_tick.add_argument("--run", help="Run id for inspector tick.")
        runtime_host_tick.add_argument("--profile", help="Supervisor/inspector profile.")
        runtime_host_tick.add_argument("--driver", help="Runtime driver override.")
        runtime_host_tick.add_argument("--wait-ttl", type=int, default=3600, help="Director wait TTL seconds.")
        runtime_host_tick.add_argument("--lease-ttl", type=int, default=3600, help="Director lease TTL seconds.")
        runtime_host_tick.add_argument("--json", action="store_true", help="Print JSON.")
        runtime_host_tick.set_defaults(func=self._runtime_host_tick)

        runtime_host_rebuild = runtime_host_sub.add_parser("rebuild-projections", help="Rebuild Runtime projections from durable project event journals.")
        runtime_host_rebuild.add_argument("--project-root", action="append", default=[], help="Project root path. Repeatable.")
        runtime_host_rebuild.add_argument("--json", action="store_true", help="Print JSON.")
        runtime_host_rebuild.set_defaults(func=self._runtime_host_rebuild_projections)

        runtime_host_projection_doctor = runtime_host_sub.add_parser("projection-doctor", help="Validate declaration-driven technical projection freshness and readiness.")
        runtime_host_projection_doctor.add_argument("--project-root", action="append", required=True, help="Project root path. Repeatable.")
        runtime_host_projection_doctor.set_defaults(func=self._runtime_host_projection_doctor)
