#!/usr/bin/env python3
"""Run installed native storage maintenance using one full pinned provider."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).absolute().parents[1] / "src"))

from processforge_core.configuration import ConfigurationProvider
from processforge_core.maintenance.contracts import MaintenanceError
from processforge_core.maintenance.storage_migration import (
    StorageMigrationHost,
    StorageMigrationService,
    run_storage_migration,
)


def _absolute(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise argparse.ArgumentTypeError("absolute contained path required")
    return path


def main(
    argv: Sequence[str] | None = None,
    *,
    configuration_builder: Callable[..., ConfigurationProvider] | None = None,
    host_factory: Callable[..., StorageMigrationHost] | None = None,
) -> int:
    """Emit exactly one JSON; no CLI flag supplies a trusted safety verdict.

    Factories are native DI seams for host composition and tests. Production
    obtains both cold builders from Core composition, never imports old tools
    or starts Runtime/MCP. A missing factory is a truthful bounded refusal.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=_absolute)
    parser.add_argument("--workplace-root", type=_absolute)
    parser.add_argument("--device-config", type=_absolute)
    parser.add_argument("--evidence-dir", type=_absolute)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--inspect", action="store_true")
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--resume", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.project_root is None and args.workplace_root is None:
        parser.error("--project-root or --workplace-root required")
    operation: Literal["inspect", "apply", "resume"] = (
        "apply" if args.apply else "resume" if args.resume else "inspect"
    )
    try:
        if configuration_builder is None or host_factory is None:
            from processforge_core import composition

            configuration_builder = configuration_builder or getattr(
                composition, "build_configuration_provider", None
            )
            host_factory = host_factory or getattr(
                composition, "build_storage_migration_host", None
            )
        if configuration_builder is None or host_factory is None:
            raise MaintenanceError("storage_host_factory_unavailable")
        provider = configuration_builder(
            device_config_path=args.device_config,
            workplace_root=args.workplace_root,
            project_root=args.project_root,
        )
        snapshot = provider.snapshot()
        if snapshot.errors:
            raise MaintenanceError("storage_configuration_invalid")
        pinned = ConfigurationProvider.pinned(snapshot.config, errors=snapshot.errors)
        host = host_factory(
            project_root=args.project_root,
            workplace_root=args.workplace_root,
            device_config_path=args.device_config,
            configuration=pinned,
            evidence_dir=args.evidence_dir,
        )
        if not isinstance(host, StorageMigrationHost):
            raise MaintenanceError("storage_host_factory_invalid")
        # Host verifies enrollment, effective target/profile/owner and evidence
        # containment. An explicit selector must stay in owner maintenance roots.
        if args.evidence_dir is not None:
            from processforge_core.maintenance.storage_migration import (
                storage_owner_root,
                validate_storage_context,
            )

            roots = {
                storage_owner_root(host.context, t)
                for t in validate_storage_context(host.context)
            }
            if not any(
                args.evidence_dir.is_relative_to(root / "maintenance")
                and args.evidence_dir != root / "maintenance"
                for root in roots
            ):
                raise MaintenanceError("storage_evidence_unsafe")
        result = run_storage_migration(host, operation=operation)
    except Exception as error:
        result = StorageMigrationService._failure(
            StorageMigrationService._report("storage-" + operation), error
        )
    print(
        json.dumps(
            result,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    )
    return 1 if result.get("blocked") or result.get("status") == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
