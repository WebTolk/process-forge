"""Register existing CLI commands for coordination."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class DirectorCommandParser:
    """Register the existing director command family."""

    def __init__(
        self,
        *,
        agent_director_run: Callable[[argparse.Namespace], int],
        agent_director_status: Callable[[argparse.Namespace], int],
        agent_director_tick: Callable[[argparse.Namespace], int],
        director_case_refresh: Callable[[argparse.Namespace], int],
        director_inbox_submit: Callable[[argparse.Namespace], int],
        error_route: Callable[[argparse.Namespace], int],
    ) -> None:
        self._agent_director_run = agent_director_run
        self._agent_director_status = agent_director_status
        self._agent_director_tick = agent_director_tick
        self._director_case_refresh = director_case_refresh
        self._director_inbox_submit = director_inbox_submit
        self._error_route = error_route

    def register_inbox(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        director_inbox_submit = add_parser("director-inbox-submit", help="Submit a file-only message to the workplace Director inbox.")
        director_inbox_submit.add_argument("--project-root", help="Project root for project-scoped messages.")
        director_inbox_submit.add_argument("--workplace", help="Workplace root or workplace.yaml for workspace messages or override.")
        director_inbox_submit.add_argument("--message-type", default="worker_report", choices=["worker_report", "error_report", "decision_request", "operator_note"], help="Director inbox message type.")
        director_inbox_submit.add_argument("--content", default="", help="Short message content.")
        director_inbox_submit.add_argument("--allow-simple-submit", action="store_true", help="Allow project-scoped submit from simple mode.")
        director_inbox_submit.add_argument("--json", action="store_true", help="Print JSON.")
        director_inbox_submit.set_defaults(func=self._director_inbox_submit)

        director_case_refresh = add_parser("director-case-refresh", help="Refresh workplace Director cases from snapshots and inbox messages.")
        director_case_refresh.add_argument("--workplace", required=True, help="Workplace root or workplace.yaml.")
        director_case_refresh.add_argument("--include-simple", action="store_true", help="Include simple projects in cases.")
        director_case_refresh.add_argument("--json", action="store_true", help="Print JSON.")
        director_case_refresh.set_defaults(func=self._director_case_refresh)

        error_route = add_parser("error-route", help="Record a project error workflow decision respecting effective coordination mode.")
        error_route.add_argument("--project-root", required=True, help="Project root path.")
        error_route.add_argument("--workplace", help="Workplace root or workplace.yaml override.")
        error_route.add_argument("--mode", default="none", choices=["none", "director_inbox", "route_to_process", "needs_operator"], help="Error workflow mode.")
        error_route.add_argument("--fallback-if-no-director", default="fail_validation", choices=["needs_operator", "fail_validation"], help="Fallback for director_inbox when project is not organized.")
        error_route.add_argument("--summary", default="", help="Error summary.")
        error_route.add_argument("--json", action="store_true", help="Print JSON.")
        error_route.set_defaults(func=self._error_route)

    def register_scheduling(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        agent_director_tick = add_parser("agent-director-tick", help="Run one Agent Director scheduling tick.")
        agent_director_tick.add_argument("--workplace", required=True, help="Workplace root path.")
        agent_director_tick.add_argument("--project-root", required=True, help="Project root path.")
        agent_director_tick.add_argument("--project-id", help="Optional project id filter.")
        agent_director_tick.add_argument("--wait-ttl", type=int, default=3600, help="Seconds before waiting handoff needs operator.")
        agent_director_tick.add_argument("--lease-ttl", type=int, default=3600, help="Lease TTL seconds.")
        agent_director_tick.set_defaults(func=self._agent_director_tick)

        agent_director_run = add_parser("agent-director-run", help="Run bounded Agent Director ticks.")
        agent_director_run.add_argument("--workplace", required=True, help="Workplace root path.")
        agent_director_run.add_argument("--project-root", required=True, help="Project root path.")
        agent_director_run.add_argument("--project-id", help="Optional project id filter.")
        agent_director_run.add_argument("--wait-ttl", type=int, default=3600, help="Seconds before waiting handoff needs operator.")
        agent_director_run.add_argument("--lease-ttl", type=int, default=3600, help="Lease TTL seconds.")
        agent_director_run.add_argument("--max-ticks", type=int, default=1, help="Maximum ticks.")
        agent_director_run.add_argument("--interval", type=float, default=0, help="Seconds between ticks.")
        agent_director_run.set_defaults(func=self._agent_director_run)

        agent_director_status = add_parser("agent-director-status", help="Show Agent Director handoff queue status.")
        agent_director_status.add_argument("--project-root", required=True, help="Project root path.")
        agent_director_status.add_argument("--json", action="store_true", help="Print JSON.")
        agent_director_status.set_defaults(func=self._agent_director_status)


class OrchestrationCommandParser:
    """Register the existing orchestration command family."""

    def __init__(
        self,
        *,
        orchestrator_plan_apply: Callable[[argparse.Namespace], int],
        orchestrator_plan_create: Callable[[argparse.Namespace], int],
        orchestrator_plan_status: Callable[[argparse.Namespace], int],
        orchestrator_plan_validate: Callable[[argparse.Namespace], int],
        worker_launch_prompt_create: Callable[[argparse.Namespace], int],
    ) -> None:
        self._orchestrator_plan_apply = orchestrator_plan_apply
        self._orchestrator_plan_create = orchestrator_plan_create
        self._orchestrator_plan_status = orchestrator_plan_status
        self._orchestrator_plan_validate = orchestrator_plan_validate
        self._worker_launch_prompt_create = worker_launch_prompt_create

    def register_plan_prompt(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        orchestrator_plan = add_parser("orchestrator-plan", help="Create, validate, apply, or inspect a multi-agent orchestration plan.")
        orchestrator_plan_sub = orchestrator_plan.add_subparsers(dest="orchestrator_plan_command", required=True)
        orchestrator_plan_create = orchestrator_plan_sub.add_parser("create", help="Create an orchestrator task plan.")
        orchestrator_plan_create.add_argument("--project-root", required=True, help="Project root path.")
        orchestrator_plan_create.add_argument("--run", required=True, help="Run id.")
        orchestrator_plan_create.add_argument("--title", required=True, help="Run title.")
        orchestrator_plan_create.add_argument("--answers", help="Optional full orchestrator task plan YAML.")
        orchestrator_plan_create.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        orchestrator_plan_create.add_argument("--apply", action="store_true", help="Write the plan.")
        orchestrator_plan_create.set_defaults(func=self._orchestrator_plan_create)
        orchestrator_plan_validate = orchestrator_plan_sub.add_parser("validate", help="Validate an orchestrator task plan.")
        orchestrator_plan_validate.add_argument("--project-root", required=True, help="Project root path.")
        orchestrator_plan_validate.add_argument("--plan", help="Plan YAML path.")
        orchestrator_plan_validate.add_argument("--run", help="Run id when --plan is omitted.")
        orchestrator_plan_validate.add_argument("--write-normalized", help="Optional normalized plan YAML output path.")
        orchestrator_plan_validate.set_defaults(func=self._orchestrator_plan_validate)
        orchestrator_plan_apply = orchestrator_plan_sub.add_parser("apply", help="Apply an orchestrator task plan.")
        orchestrator_plan_apply.add_argument("--project-root", required=True, help="Project root path.")
        orchestrator_plan_apply.add_argument("--plan", help="Plan YAML path.")
        orchestrator_plan_apply.add_argument("--run", help="Run id when --plan is omitted.")
        orchestrator_plan_apply.add_argument("--workplace", help="Workplace root path for lease grants.")
        orchestrator_plan_apply.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        orchestrator_plan_apply.add_argument("--apply", action="store_true", help="Create run, tasks, capsules, prompts, and handoff.")
        orchestrator_plan_apply.set_defaults(func=self._orchestrator_plan_apply, shell_plan=False)
        orchestrator_plan_status = orchestrator_plan_sub.add_parser("status", help="Show orchestration status.")
        orchestrator_plan_status.add_argument("--project-root", required=True, help="Project root path.")
        orchestrator_plan_status.add_argument("--plan", help="Plan YAML path.")
        orchestrator_plan_status.add_argument("--run", help="Run id when --plan is omitted.")
        orchestrator_plan_status.set_defaults(func=self._orchestrator_plan_status)

        worker_launch_prompt = add_parser("worker-launch-prompt", help="Create a bounded launch prompt for a worker task.")
        worker_launch_prompt_sub = worker_launch_prompt.add_subparsers(dest="worker_launch_prompt_command", required=True)
        worker_launch_prompt_create = worker_launch_prompt_sub.add_parser("create", help="Create a worker launch prompt.")
        worker_launch_prompt_create.add_argument("--project-root", required=True, help="Project root path.")
        worker_launch_prompt_create.add_argument("--task", required=True, help="Task id.")
        worker_launch_prompt_create.add_argument("--output", help="Optional output path.")
        worker_launch_prompt_create.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        worker_launch_prompt_create.add_argument("--apply", action="store_true", help="Write the prompt.")
        worker_launch_prompt_create.set_defaults(func=self._worker_launch_prompt_create)

        orchestrator_plan_create_alias = add_parser("orchestrator-plan-create", help="Flat alias for orchestrator-plan create.")
        orchestrator_plan_create_alias.add_argument("--project-root", required=True, help="Project root path.")
        orchestrator_plan_create_alias.add_argument("--run", required=True, help="Run id.")
        orchestrator_plan_create_alias.add_argument("--title", required=True, help="Run title.")
        orchestrator_plan_create_alias.add_argument("--answers", help="Optional full orchestrator task plan YAML.")
        orchestrator_plan_create_alias.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        orchestrator_plan_create_alias.add_argument("--apply", action="store_true", help="Write the plan.")
        orchestrator_plan_create_alias.set_defaults(func=self._orchestrator_plan_create)

        orchestrator_plan_validate_alias = add_parser("orchestrator-plan-validate", help="Flat alias for orchestrator-plan validate.")
        orchestrator_plan_validate_alias.add_argument("--project-root", required=True, help="Project root path.")
        orchestrator_plan_validate_alias.add_argument("--plan", help="Plan YAML path.")
        orchestrator_plan_validate_alias.add_argument("--run", help="Run id when --plan is omitted.")
        orchestrator_plan_validate_alias.add_argument("--write-normalized", help="Optional normalized plan YAML output path.")
        orchestrator_plan_validate_alias.set_defaults(func=self._orchestrator_plan_validate)

        orchestrator_plan_apply_alias = add_parser("orchestrator-plan-apply", help="Flat alias for orchestrator-plan apply.")
        orchestrator_plan_apply_alias.add_argument("--project-root", required=True, help="Project root path.")
        orchestrator_plan_apply_alias.add_argument("--plan", help="Plan YAML path.")
        orchestrator_plan_apply_alias.add_argument("--run", help="Run id when --plan is omitted.")
        orchestrator_plan_apply_alias.add_argument("--workplace", help="Workplace root path for lease grants.")
        orchestrator_plan_apply_alias.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        orchestrator_plan_apply_alias.add_argument("--apply", action="store_true", help="Create run, tasks, capsules, prompts, and handoff.")
        orchestrator_plan_apply_alias.set_defaults(func=self._orchestrator_plan_apply, shell_plan=False)

        orchestrator_plan_status_alias = add_parser("orchestrator-plan-status", help="Flat alias for orchestrator-plan status.")
        orchestrator_plan_status_alias.add_argument("--project-root", required=True, help="Project root path.")
        orchestrator_plan_status_alias.add_argument("--plan", help="Plan YAML path.")
        orchestrator_plan_status_alias.add_argument("--run", help="Run id when --plan is omitted.")
        orchestrator_plan_status_alias.set_defaults(func=self._orchestrator_plan_status)

        worker_launch_prompt_create_alias = add_parser("worker-launch-prompt-create", help="Flat alias for worker-launch-prompt create.")
        worker_launch_prompt_create_alias.add_argument("--project-root", required=True, help="Project root path.")
        worker_launch_prompt_create_alias.add_argument("--task", required=True, help="Task id.")
        worker_launch_prompt_create_alias.add_argument("--output", help="Optional output path.")
        worker_launch_prompt_create_alias.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        worker_launch_prompt_create_alias.add_argument("--apply", action="store_true", help="Write the prompt.")
        worker_launch_prompt_create_alias.set_defaults(func=self._worker_launch_prompt_create)

    def register_shell_aliases(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        for alias_name, func, help_text in [
            ("orchestrator-shell-plan-create", self._orchestrator_plan_create, "Flat alias for orchestrator-plan create with shell-agent policy support."),
            ("orchestrator-shell-plan-validate", self._orchestrator_plan_validate, "Flat alias for orchestrator-plan validate with shell-agent policy support."),
            ("orchestrator-shell-plan-apply", self._orchestrator_plan_apply, "Flat alias for orchestrator-plan apply with shell-agent policy support."),
        ]:
            shell_plan = add_parser(alias_name, help=help_text)
            shell_plan.add_argument("--project-root", required=True, help="Project root path.")
            if alias_name.endswith("create"):
                shell_plan.add_argument("--run", required=True, help="Run id.")
                shell_plan.add_argument("--title", required=True, help="Run title.")
                shell_plan.add_argument("--answers", help="Optional full orchestrator shell-agent plan YAML.")
                shell_plan.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
                shell_plan.add_argument("--apply", action="store_true", help="Write the plan.")
            else:
                shell_plan.add_argument("--plan", help="Plan YAML path.")
                shell_plan.add_argument("--run", help="Run id when --plan is omitted.")
                if alias_name.endswith("apply"):
                    shell_plan.add_argument("--workplace", help="Workplace root path for lease grants.")
                    shell_plan.add_argument("--model", help="Optional agent model passed to shell workers in this multi-agent plan.")
                    shell_plan.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
                    shell_plan.add_argument("--apply", action="store_true", help="Create run, tasks, capsules, prompts, leases, and supervisor runs.")
                else:
                    shell_plan.add_argument("--write-normalized", help="Optional normalized plan YAML output path.")
            shell_plan.set_defaults(func=func, shell_plan=alias_name.endswith("apply"))


class HandoffCommandParser:
    """Register the existing handoffs command family."""

    def __init__(
        self,
        *,
        handoff_accept: Callable[[argparse.Namespace], int],
        handoff_create: Callable[[argparse.Namespace], int],
        handoff_doctor: Callable[[argparse.Namespace], int],
        handoff_finalize: Callable[[argparse.Namespace], int],
        handoff_offer: Callable[[argparse.Namespace], int],
        handoff_return: Callable[[argparse.Namespace], int],
        handoff_start_target_run: Callable[[argparse.Namespace], int],
        handoff_status: Callable[[argparse.Namespace], int],
        process_route_doctor: Callable[[argparse.Namespace], int],
        process_route_list: Callable[[argparse.Namespace], int],
        process_route_validate: Callable[[argparse.Namespace], int],
    ) -> None:
        self._handoff_accept = handoff_accept
        self._handoff_create = handoff_create
        self._handoff_doctor = handoff_doctor
        self._handoff_finalize = handoff_finalize
        self._handoff_offer = handoff_offer
        self._handoff_return = handoff_return
        self._handoff_start_target_run = handoff_start_target_run
        self._handoff_status = handoff_status
        self._process_route_doctor = process_route_doctor
        self._process_route_list = process_route_list
        self._process_route_validate = process_route_validate

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        process_route_list = add_parser("process-route-list", help="List process route map entries.")
        process_route_list.add_argument("--project-root", required=True, help="Project root path.")
        process_route_list.add_argument("--json", action="store_true", help="Print JSON.")
        process_route_list.set_defaults(func=self._process_route_list)
        process_route_validate = add_parser("process-route-validate", help="Validate process routes.")
        process_route_validate.add_argument("--project-root", required=True, help="Project root path.")
        process_route_validate.set_defaults(func=self._process_route_validate)
        process_route_doctor = add_parser("process-route-doctor", help="Doctor process routes.")
        process_route_doctor.add_argument("--project-root", required=True, help="Project root path.")
        process_route_doctor.set_defaults(func=self._process_route_doctor)

        handoff_create = add_parser("handoff-create", help="Create a formal process handoff package from a route.")
        handoff_create.add_argument("--project-root", required=True, help="Project root path.")
        handoff_create.add_argument("--route", required=True, help="Route id.")
        handoff_create.add_argument("--from-run", required=True, help="Source run id.")
        handoff_create.add_argument("--from-stage", help="Source stage id.")
        handoff_create.add_argument("--id", help="Handoff id.")
        handoff_create.add_argument("--apply", action="store_true", help="Write the handoff package.")
        handoff_create.set_defaults(func=self._handoff_create)

        for name, func, help_text in [
            ("handoff-offer", self._handoff_offer, "Offer/show a handoff to available agents."),
            ("handoff-status", self._handoff_status, "Show handoff status."),
        ]:
            handoff_status = add_parser(name, help=help_text)
            handoff_status.add_argument("--project-root", required=True, help="Project root path.")
            handoff_status.add_argument("--handoff", required=True, help="Handoff id.")
            handoff_status.add_argument("--workplace", help="Workplace root path for availability lookup.")
            handoff_status.add_argument("--project-id", help="Optional project id filter.")
            handoff_status.add_argument("--json", action="store_true", help="Print JSON.")
            handoff_status.set_defaults(func=func)

        handoff_accept = add_parser("handoff-accept", help="Accept a handoff.")
        handoff_accept.add_argument("--project-root", required=True, help="Project root path.")
        handoff_accept.add_argument("--handoff", required=True, help="Handoff id.")
        handoff_accept.add_argument("--agent", required=True, help="Agent id.")
        handoff_accept.add_argument("--session", help="Session id.")
        handoff_accept.set_defaults(func=self._handoff_accept)

        handoff_start = add_parser("handoff-start-target-run", help="Start or attach a target run for a handoff.")
        handoff_start.add_argument("--project-root", required=True, help="Project root path.")
        handoff_start.add_argument("--handoff", required=True, help="Handoff id.")
        handoff_start.add_argument("--run", help="Target run id.")
        handoff_start.set_defaults(func=self._handoff_start_target_run)

        handoff_return = add_parser("handoff-return", help="Return handoff results to the source process.")
        handoff_return.add_argument("--project-root", required=True, help="Project root path.")
        handoff_return.add_argument("--handoff", required=True, help="Handoff id.")
        handoff_return.add_argument("--artifact", action="append", default=[], help="Returned artifact path. Repeatable.")
        handoff_return.set_defaults(func=self._handoff_return)

        handoff_finalize = add_parser("handoff-finalize", help="Finalize a handoff.")
        handoff_finalize.add_argument("--project-root", required=True, help="Project root path.")
        handoff_finalize.add_argument("--handoff", required=True, help="Handoff id.")
        handoff_finalize.set_defaults(func=self._handoff_finalize)

        handoff_doctor = add_parser("handoff-doctor", help="Validate handoff packages.")
        handoff_doctor.add_argument("--project-root", required=True, help="Project root path.")
        handoff_doctor.set_defaults(func=self._handoff_doctor)
