"""Execute one CLI invocation using the published parser and handlers."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from processforge_core import diagnostics


class CliApplication:
    """Own invocation ordering; command policy stays with existing handlers."""

    def __init__(
        self,
        *,
        parser_factory: Callable[[], argparse.ArgumentParser],
        project_id_resolver: Callable[[Path], str],
        entry_file: str | Path,
    ) -> None:
        self._parser_factory = parser_factory
        self._project_id_resolver = project_id_resolver
        self._entry_file = entry_file

    def run(self, argv: list[str] | None = None) -> int:
        parser = self._parser_factory()
        args = parser.parse_args(argv)
        strict_authoring_commands = {
            "authoring-transaction-recover",
            "knowledge-add-url",
            "knowledge-add-resource",
            "platform-contract-install",
            "platform-create",
            "process-authoring-apply",
            "process-create",
        }
        apply_optional = (
            (args.command == "workplace-setup" and getattr(args, "workplace_setup_command", "") in {"review", "status"})
            or args.command == "project-context-refresh"
        )
        if hasattr(args, "apply") and args.apply and getattr(args, "dry_run", False):
            parser.error("choose either --dry-run or --apply")
        if args.command in strict_authoring_commands and not (
            bool(getattr(args, "apply", False)) ^ bool(getattr(args, "dry_run", False))
        ):
            parser.error("choose exactly one of --dry-run or --apply")
        if (
            hasattr(args, "apply")
            and not args.apply
            and not apply_optional
            and args.command not in strict_authoring_commands
        ):
            if not getattr(args, "dry_run", False):
                args.mode_implicit = True
            args.dry_run = True
        # Initialization owns its post-preflight events. Eager CLI diagnostics must
        # not turn status, a preview, or an entry refusal into a project write.
        if args.command in {"agent-entry", "agent-start-prompt", "init-project", "project-init", "project-onboard", "project-init-status", "project-init-repair", "diagnostics-status", "diagnostics-export", "diagnostics-configure", "monitor", "config"} or (args.command == "server" and args.runtime_command == "status"):
            return args.func(args)
        project_value = getattr(args, "project_root", None)
        project = Path(project_value).expanduser().resolve() if isinstance(project_value, str) else None
        run_id = getattr(args, "run", None)
        session_id = getattr(args, "session", None)
        options = diagnostics.invocation_options(args.diagnostic_profile, args.diagnostic_threshold, args.diagnostic_components, args.diagnostic_sink)
        logger = diagnostics.for_project(project, run_id=run_id, session_id=session_id, invocation=options)
        with diagnostics.operation(logger, "cli", str(args.command), project_id=self._project_id_resolver(project) if project and (project / ".pf").is_dir() else None,
                                   run_id=run_id, session_id=session_id or None, build=diagnostics.identity_for(logger, self._entry_file)):
            result = args.func(args)
            if result:
                diagnostics.emit("error", "cli.nonzero_exit", {"exit_code": result}, component="cli")
            return result
