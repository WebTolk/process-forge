"""Register existing CLI commands for agents."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class AgentPresenceCommandParser:
    """Register the existing presence command family."""

    def __init__(
        self,
        *,
        agent_availability: Callable[[argparse.Namespace], int],
        agent_checkin: Callable[[argparse.Namespace], int],
        agent_checkout: Callable[[argparse.Namespace], int],
        agent_heartbeat: Callable[[argparse.Namespace], int],
        agent_ledger_doctor: Callable[[argparse.Namespace], int],
        agent_list: Callable[[argparse.Namespace], int],
        agent_register: Callable[[argparse.Namespace], int],
        agent_status: Callable[[argparse.Namespace], int],
        session_start: Callable[[argparse.Namespace], int],
    ) -> None:
        self._agent_availability = agent_availability
        self._agent_checkin = agent_checkin
        self._agent_checkout = agent_checkout
        self._agent_heartbeat = agent_heartbeat
        self._agent_ledger_doctor = agent_ledger_doctor
        self._agent_list = agent_list
        self._agent_register = agent_register
        self._agent_status = agent_status
        self._session_start = session_start

    def register_session_start(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        session_start = add_parser("session-start", help="Start or inspect a ProcessForge session; with --agent, records an agent check-in.")
        session_start.add_argument("--mode", choices=["resume", "project_init", "assignment_execute", "context_resolve", "context_compile", "doctor_context"], help="Session bootstrap mode.")
        session_start.add_argument("--project-root", help="Project root path.")
        session_start.add_argument("--assignment", help="Optional assignment path loaded for telemetry.")
        session_start.add_argument("--allow-write", action="store_true", help="Write artifacts/session-status-report.md.")
        session_start.add_argument("--report-only", action="store_true", help="Do not write public artifacts. Private telemetry is still written.")
        session_start.add_argument("--rebuild-context-if-stale", action="store_true", help="Run context resolution when context is missing or stale.")
        session_start.add_argument("--workplace", help="Workplace root path for agent session check-in. Defaults from --project-root when the project is onboarded.")
        session_start.add_argument("--agent", help="Agent id for agent session check-in.")
        session_start.add_argument("--session", help="Session id. Defaults to generated id.")
        session_start.add_argument("--project-id", help="Project id override.")
        session_start.add_argument("--process", help="Process id.")
        session_start.add_argument("--run", help="Run id.")
        session_start.add_argument("--task", help="Task id.")
        session_start.add_argument("--specialization", action="append", default=[], help="Selected specialization id for this session. Repeatable.")
        session_start.add_argument("--role", action="append", default=[], help="Checked-in role. Repeatable.")
        session_start.add_argument("--capability", action="append", default=[], help="Runtime capability. Repeatable.")
        session_start.add_argument("--supports-specialization", action="append", default=[], help="Specialization id supported by this agent session. Repeatable.")
        session_start.add_argument("--ttl", type=int, default=300, help="Heartbeat TTL seconds.")
        session_start.add_argument("--json", action="store_true", help="Print JSON for agent session check-in.")
        session_start.set_defaults(func=self._session_start)

    def register_attendance(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        agent_register = add_parser("agent-register", help="Register an agent in the workplace agent registry.")
        agent_register.add_argument("--workplace", required=True, help="Workplace root path.")
        agent_register.add_argument("--agent", required=True, help="Agent id.")
        agent_register.add_argument("--title", help="Agent title.")
        agent_register.add_argument("--kind", default="operator_started_agent", help="Agent kind.")
        agent_register.add_argument("--role", action="append", default=[], help="Agent role. Repeatable.")
        agent_register.add_argument("--capability", action="append", default=[], help="Agent capability. Repeatable.")
        agent_register.add_argument("--supports-specialization", action="append", default=[], help="Specialization id this agent profile supports. Repeatable.")
        agent_register.set_defaults(func=self._agent_register)

        agent_list = add_parser("agent-list", help="List registered workplace agents.")
        agent_list.add_argument("--workplace", required=True, help="Workplace root path.")
        agent_list.add_argument("--json", action="store_true", help="Print JSON.")
        agent_list.set_defaults(func=self._agent_list)

        agent_checkin = add_parser("agent-checkin", help="Record an agent session check-in and current presence.")
        agent_checkin.add_argument("--workplace", help="Workplace root path. Defaults from --project-root when the project is onboarded.")
        agent_checkin.add_argument("--agent", required=True, help="Agent id.")
        agent_checkin.add_argument("--session", help="Session id. Defaults to generated id.")
        agent_checkin.add_argument("--project-root", help="Project root path.")
        agent_checkin.add_argument("--project-id", help="Project id override.")
        agent_checkin.add_argument("--process", help="Process id.")
        agent_checkin.add_argument("--run", help="Run id.")
        agent_checkin.add_argument("--task", help="Task id.")
        agent_checkin.add_argument("--role", action="append", default=[], help="Checked-in role. Repeatable.")
        agent_checkin.add_argument("--capability", action="append", default=[], help="Runtime capability. Repeatable.")
        agent_checkin.add_argument("--supports-specialization", action="append", default=[], help="Specialization id supported by this session. Repeatable.")
        agent_checkin.add_argument("--ttl", type=int, default=300, help="Heartbeat TTL seconds.")
        agent_checkin.add_argument("--json", action="store_true", help="Print JSON.")
        agent_checkin.set_defaults(func=self._agent_checkin)

        agent_heartbeat = add_parser("agent-heartbeat", help="Refresh an agent session presence record.")
        agent_heartbeat.add_argument("--workplace", help="Workplace root path. Defaults from --project-root when the project is onboarded.")
        agent_heartbeat.add_argument("--agent", help="Agent id. Optional when --session or --project-root current session is supplied.")
        agent_heartbeat.add_argument("--session", help="Session id.")
        agent_heartbeat.add_argument("--project-root", help="Project root path for current-session lookup.")
        agent_heartbeat.add_argument("--task", help="Current task id.")
        agent_heartbeat.set_defaults(func=self._agent_heartbeat)

        agent_checkout = add_parser("agent-checkout", help="Record an agent session checkout.")
        agent_checkout.add_argument("--workplace", help="Workplace root path. Defaults from --project-root when the project is onboarded.")
        agent_checkout.add_argument("--agent", help="Agent id. Optional when --session or --project-root current session is supplied.")
        agent_checkout.add_argument("--session", help="Session id.")
        agent_checkout.add_argument("--project-root", help="Project root path for current-session lookup.")
        agent_checkout.set_defaults(func=self._agent_checkout)

        agent_status = add_parser("agent-status", help="Show current agent session presence.")
        agent_status.add_argument("--workplace", help="Workplace root path. Defaults from --project-root when the project is onboarded.")
        agent_status.add_argument("--agent", help="Agent id.")
        agent_status.add_argument("--session", help="Session id.")
        agent_status.add_argument("--project-root", help="Project root path filter.")
        agent_status.add_argument("--project-id", help="Project id filter.")
        agent_status.add_argument("--json", action="store_true", help="Print JSON.")
        agent_status.set_defaults(func=self._agent_status)

        session_heartbeat = add_parser("session-heartbeat", help="Thin alias for agent-heartbeat.")
        session_heartbeat.add_argument("--workplace", help="Workplace root path. Defaults from --project-root when the project is onboarded.")
        session_heartbeat.add_argument("--agent", help="Agent id.")
        session_heartbeat.add_argument("--session", help="Session id.")
        session_heartbeat.add_argument("--project-root", help="Project root path for current-session lookup.")
        session_heartbeat.add_argument("--task", help="Current task id.")
        session_heartbeat.set_defaults(func=self._agent_heartbeat)

        session_end = add_parser("session-end", help="Thin alias for agent-checkout.")
        session_end.add_argument("--workplace", help="Workplace root path. Defaults from --project-root when the project is onboarded.")
        session_end.add_argument("--agent", help="Agent id.")
        session_end.add_argument("--session", help="Session id.")
        session_end.add_argument("--project-root", help="Project root path for current-session lookup.")
        session_end.set_defaults(func=self._agent_checkout)

        session_status = add_parser("session-status", help="Thin alias for agent-status.")
        session_status.add_argument("--workplace", help="Workplace root path. Defaults from --project-root when the project is onboarded.")
        session_status.add_argument("--agent", help="Agent id.")
        session_status.add_argument("--session", help="Session id.")
        session_status.add_argument("--project-root", help="Project root path filter.")
        session_status.add_argument("--project-id", help="Project id filter.")
        session_status.add_argument("--json", action="store_true", help="Print JSON.")
        session_status.set_defaults(func=self._agent_status)

        agent_availability = add_parser("agent-availability", help="Answer whether a checked-in agent with a role is available.")
        agent_availability.add_argument("--workplace", help="Workplace root path. Defaults from --project-root when the project is onboarded.")
        agent_availability.add_argument("--role", required=True, help="Required role.")
        agent_availability.add_argument("--project-root", help="Project root path for workplace and project-id filter.")
        agent_availability.add_argument("--project-id", help="Optional project id filter.")
        agent_availability.add_argument("--json", action="store_true", help="Print JSON.")
        agent_availability.set_defaults(func=self._agent_availability)

        agent_ledger_doctor = add_parser("agent-ledger-doctor", help="Validate workplace agent registry, ledger, and presence.")
        agent_ledger_doctor.add_argument("--workplace", required=True, help="Workplace root path.")
        agent_ledger_doctor.set_defaults(func=self._agent_ledger_doctor)


class AgentLeaseCommandParser:
    """Register the existing leases command family."""

    def __init__(
        self,
        *,
        agent_lease_doctor: Callable[[argparse.Namespace], int],
        agent_lease_grant: Callable[[argparse.Namespace], int],
        agent_lease_list: Callable[[argparse.Namespace], int],
        agent_lease_release: Callable[[argparse.Namespace], int],
        agent_lease_revoke: Callable[[argparse.Namespace], int],
    ) -> None:
        self._agent_lease_doctor = agent_lease_doctor
        self._agent_lease_grant = agent_lease_grant
        self._agent_lease_list = agent_lease_list
        self._agent_lease_release = agent_lease_release
        self._agent_lease_revoke = agent_lease_revoke

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        agent_lease_grant = add_parser("agent-lease-grant", help="Grant an agent lease/key.")
        agent_lease_grant.add_argument("--workplace", required=True, help="Workplace root path.")
        agent_lease_grant.add_argument("--id", help="Lease id.")
        agent_lease_grant.add_argument("--agent", required=True, help="Agent id.")
        agent_lease_grant.add_argument("--session", help="Session id.")
        agent_lease_grant.add_argument("--project-id", help="Project id.")
        agent_lease_grant.add_argument("--process", help="Process id.")
        agent_lease_grant.add_argument("--run", help="Run id.")
        agent_lease_grant.add_argument("--task", help="Task id.")
        agent_lease_grant.add_argument("--capsule", help="Assignment capsule path.")
        agent_lease_grant.add_argument("--allowed-file", action="append", default=[], help="Allowed file/glob. Repeatable.")
        agent_lease_grant.add_argument("--allowed-read-file", action="append", default=[], help="Allowed read file/glob. Repeatable.")
        agent_lease_grant.add_argument("--forbidden-file", action="append", default=[], help="Forbidden file/glob. Repeatable.")
        agent_lease_grant.add_argument("--ttl", type=int, default=3600, help="Lease TTL seconds.")
        agent_lease_grant.set_defaults(func=self._agent_lease_grant)

        for name, func, help_text in [
            ("agent-lease-release", self._agent_lease_release, "Release an active agent lease."),
            ("agent-lease-revoke", self._agent_lease_revoke, "Revoke an agent lease."),
        ]:
            lease_status = add_parser(name, help=help_text)
            lease_status.add_argument("--workplace", required=True, help="Workplace root path.")
            lease_status.add_argument("--lease", required=True, help="Lease id.")
            lease_status.set_defaults(func=func)

        agent_lease_list = add_parser("agent-lease-list", help="List agent leases.")
        agent_lease_list.add_argument("--workplace", required=True, help="Workplace root path.")
        agent_lease_list.add_argument("--json", action="store_true", help="Print JSON.")
        agent_lease_list.set_defaults(func=self._agent_lease_list)

        agent_lease_doctor = add_parser("agent-lease-doctor", help="Validate agent leases.")
        agent_lease_doctor.add_argument("--workplace", required=True, help="Workplace root path.")
        agent_lease_doctor.set_defaults(func=self._agent_lease_doctor)
