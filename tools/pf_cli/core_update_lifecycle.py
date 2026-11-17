"""Compose existing Runtime stop, Core file update and target Runtime start."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

from processforge_core.common.properties import DistributionMetadataReader
from processforge_core.maintenance.update import (
    CoreUpdateError,
    apply_update,
    build_plan,
    read_archive_manifest,
    resume_file_update,
    validate_archive_payload,
)


def managed_core_update(
    args: argparse.Namespace, core: Any, *, resume: bool = False
) -> tuple[dict[str, Any], int]:
    """Run only the explicitly selected lifecycle; never migrate project data."""
    if not args.confirm:
        raise CoreUpdateError(
            "confirm_required", "Runtime management requires --confirm"
        )
    if not args.workplace_root:
        raise CoreUpdateError(
            "workplace_required", "Runtime management requires --workplace-root"
        )
    if not args.archive:
        raise CoreUpdateError(
            "archive_required", "Runtime management requires --archive"
        )
    timeout = float(args.runtime_timeout)
    if not math.isfinite(timeout) or timeout <= 0:
        raise CoreUpdateError(
            "invalid_timeout", "Runtime timeout must be finite and positive"
        )

    from processforge_core.maintenance.file_update import (
        file_update_candidate,
        require_update_target,
    )

    target = Path(args.core_root).expanduser().absolute()
    archive = Path(args.archive).expanduser().absolute()
    workplace = Path(args.workplace_root).expanduser().absolute()
    if not file_update_candidate(target):
        raise CoreUpdateError(
            "plan_blocked", "Runtime management requires an external verified updater"
        )
    target = require_update_target(target)
    # Preflight before contacting the service. The file updater revalidates its
    # frozen input and takes the existing singleton mutex after the guarded stop.
    if resume:
        manifest = read_archive_manifest(archive)
        validate_archive_payload(archive, manifest)
    else:
        plan = build_plan(target, archive)
        if plan["status"] == "blocked":
            raise CoreUpdateError(
                "plan_blocked",
                "Core update preflight blockers: "
                + json.dumps(plan.get("blockers", []), sort_keys=True),
            )

    from pf_runtime import service

    stop_args = argparse.Namespace(
        command="server", workplace=str(workplace), force=False, timeout=timeout
    )
    try:
        # This is a single CLI invocation, not a shared server stdout capture.
        with contextlib.redirect_stdout(io.StringIO()):
            stopped = service.command_stop(stop_args, core)
        if stopped:
            raise CoreUpdateError(
                "runtime_stop_failed", "Runtime stop did not complete"
            )
    except SystemExit as error:
        raise CoreUpdateError("runtime_stop_failed", str(error)) from None

    try:
        if resume:
            result = resume_file_update(
                target, archive, confirm=True, workplace_root=workplace
            )
        else:
            result = apply_update(
                target,
                archive,
                confirm=True,
                workplace_root=workplace,
                force_local_modifications=bool(args.force_local_modifications),
            )
    except CoreUpdateError as error:
        raise CoreUpdateError(
            error.code,
            error.message
            + "; automatic Runtime restart was not attempted; inspect Core repair status",
        ) from None

    # Execute the new installation's existing entry; the updater's loaded Core
    # never becomes the replacement service. Startup retains its normal timeout.
    lifecycle: dict[str, Any] = {"stop": "stopped", "start": "failed"}
    result["runtime_lifecycle"] = lifecycle
    try:
        started = subprocess.run(
            [
                sys.executable,
                "-B",
                str(target / "bin/pf.py"),
                "runtime",
                "start",
                "--workplace",
                str(workplace),
                "--timeout",
                str(timeout),
                "--json",
            ],
            cwd=target,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            encoding="utf-8",
        )
    except OSError as error:
        lifecycle["diagnostic"] = str(error)
        lifecycle["required_action"] = "inspect_runtime_status_and_start"
        return result, 2
    if started.returncode:
        lifecycle["exit_code"] = started.returncode
        lifecycle["diagnostic"] = (started.stdout + started.stderr).strip()
        lifecycle["required_action"] = "inspect_runtime_status_and_start"
        return result, 2
    try:
        response = json.loads(started.stdout)
    except ValueError:
        response = {}
    if not isinstance(response, dict) or response.get("status") not in {
        "started",
        "already_running",
    }:
        lifecycle["required_action"] = "inspect_runtime_status_and_start"
        return result, 2
    observed = service.inspect_lifecycle(workplace, core)
    identity_report = observed["state"].get("core_identity")
    identity = (
        identity_report.get("loaded") if isinstance(identity_report, dict) else None
    )
    installed = DistributionMetadataReader(target).read()
    if (
        observed["kind"] != "ready"
        or not isinstance(identity, dict)
        or installed.build_id == "unknown"
        or identity.get("build_id") != installed.build_id
        or observed["state"].get("pid") != response.get("pid")
    ):
        lifecycle["start"] = "identity_unverified"
        lifecycle["required_action"] = "inspect_runtime_status_and_start"
        return result, 2
    lifecycle["start"] = response
    lifecycle["instance_id"] = observed["state"].get("instance_id")
    return result, 0
