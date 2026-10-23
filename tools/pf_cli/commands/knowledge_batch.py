"""Adapt an explicit batch file to the knowledge batch Core service."""

from __future__ import annotations

import argparse
import io
import json
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

from processforge_core.common.yaml_io import load_yaml_document
from processforge_core.resources.knowledge_batch import KnowledgeBatchService


class KnowledgeBatchCommand:
    """Load one envelope, invoke Core and print a portable batch report."""

    def __init__(
        self,
        *,
        service_factory: Callable[[argparse.Namespace], KnowledgeBatchService],
        load_batch: Callable[[Path], dict[str, Any]] = load_yaml_document,
    ) -> None:
        """Save a cold, per-invocation factory and the existing YAML reader."""
        self._service_factory = service_factory
        self._load_batch = load_batch

    def execute(self, args: argparse.Namespace) -> int:
        """Print one report; mixed item or final indexing failures exit nonzero."""
        apply = bool(getattr(args, "apply", False))
        dry_run = bool(getattr(args, "dry_run", False))
        if apply and dry_run:
            report = KnowledgeBatchService.failure(
                "knowledge_batch_mode_conflict", apply=apply
            )
        else:
            try:
                batch_path = Path(args.batch_file).expanduser().resolve()
                envelope = self._load_batch(batch_path)
            except (OSError, ValueError, TypeError):
                report = KnowledgeBatchService.failure(
                    "knowledge_batch_file_unreadable", apply=apply
                )
            else:
                # Native post-commit effects print their own proposal/report
                # lines. Keep those private diagnostics out of this new surface
                # and preserve one complete JSON document when requested.
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    report = self._service_factory(args).run(
                        envelope,
                        package_id=str(args.package),
                        apply=apply,
                        dry_run=dry_run,
                    )
        if getattr(args, "json", False):
            print(
                json.dumps(report, ensure_ascii=True, sort_keys=True, allow_nan=False)
            )
        else:
            print(f"STATUS: {report['status']}")
            if report.get("error"):
                print(f"ERROR: {report['error']}")
            for row in report["results"]:
                print(
                    f"ITEM {row['index']}: {row['status']} "
                    f"{row['resource_id'] or '<unresolved>'}"
                )
                if row.get("error"):
                    print(f"ERROR: {row['error']}")
            indexing = report["indexing"]
            print(f"INDEXING: {indexing['status']}")
            if indexing.get("error"):
                print(f"ERROR: {indexing['error']}")
        return 0 if report["status"] in ("ok", "planned") else 1
