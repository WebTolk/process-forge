#!/usr/bin/env python3
"""Explicit NDJSON -> project SQLite migration. Originals stay intact.

Without --apply, validate and report a plan. --skip-invalid explicitly permits
skipping quarantined invalid records. --evidence-dir selects an evidence base.
"""

# Standalone source execution must establish the local package roots first.
# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from processforge_core.composition import build_configuration_provider
from processforge_core.configuration import ConfigurationProvider
from processforge_core.maintenance.contracts import JsonObject
from processforge_core.maintenance.journals import JournalMaintenanceService
from processforge_core.sqlite_storage import JournalError


def migrate(
    project_root: Path,
    workplace: Path,
    *,
    apply: bool = False,
    skip_invalid: bool = False,
    evidence_dir: Path | None = None,
    configuration: ConfigurationProvider | None = None,
    device_config_path: Path | None = None,
) -> JsonObject:
    """Delegate explicit migration to its owning Core service."""
    provider = (
        configuration
        if configuration is not None
        else build_configuration_provider(
            project_root=project_root.resolve(),
            workplace_root=workplace.resolve(),
            device_config_path=device_config_path,
        )
    )
    snapshot = provider.snapshot()
    pinned = ConfigurationProvider.pinned(snapshot.config, errors=snapshot.errors)
    return JournalMaintenanceService(configuration=pinned).migrate(
        project_root,
        workplace,
        apply=apply,
        skip_invalid=skip_invalid,
        evidence_dir=evidence_dir,
    )


def main() -> int:
    """Keep the released flags, JSON output and success/refusal exit mapping."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--workplace", type=Path, required=True)
    parser.add_argument("--device-config", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--skip-invalid",
        action="store_true",
        help="explicitly accept reported invalid legacy rows",
    )
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()
    try:
        report = migrate(
            args.project_root,
            args.workplace,
            apply=args.apply,
            skip_invalid=args.skip_invalid,
            evidence_dir=args.evidence_dir,
            device_config_path=args.device_config,
        )
    except (JournalError, OSError, ValueError, sqlite3.Error) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=True))
        return 1
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 1 if report["blocked"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
