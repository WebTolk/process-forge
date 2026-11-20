"""Existing authoring mode, transaction paths and read-only input checks."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..work.context_documents import ContextContractInputs
from .plans import AuthoringPlan


class AuthoringInputService:
    def __init__(self) -> None:
        self.inputs = ContextContractInputs()

    def mode(self, args: argparse.Namespace) -> str:
        apply = bool(getattr(args, "apply", False))
        dry_run = bool(getattr(args, "dry_run", False))
        if apply == dry_run:
            raise SystemExit("FAIL: choose exactly one of --dry-run or --apply")
        if apply:
            return "apply"
        return "dry_run"

    def transaction_root(self, plan: AuthoringPlan) -> Path:
        return plan.runtime_root / "authoring-transactions" / plan.transaction_id

    def journal_path(self, plan: AuthoringPlan) -> Path:
        return self.transaction_root(plan) / "journal.yaml"

    def incomplete_journals(self, runtime_root: Path) -> list[Path]:
        root = runtime_root / "authoring-transactions"
        if not root.is_dir():
            return []
        incomplete: list[Path] = []
        terminal = {"rolled_back", "committed_audit_complete"}
        for path in sorted(root.glob("*/journal.yaml")):
            data = self.inputs.load_yaml_document(path)
            if str(data.get("state") or "") not in terminal:
                incomplete.append(path)
        return incomplete

    def parent_types(self, destination: Path) -> None:
        if destination.exists() and destination.is_dir():
            raise SystemExit(f"FAIL: authoring destination is a directory: {destination}")
        parent = destination.parent
        missing: list[Path] = []
        while not parent.exists():
            missing.append(parent)
            if parent == parent.parent:
                break
            parent = parent.parent
        if parent.exists() and not parent.is_dir():
            raise SystemExit(f"FAIL: authoring destination parent is not a directory: {parent}")

    def parent_chain(self, path: Path) -> list[Path]:
        chain: list[Path] = []
        parent = path.parent
        while not parent.exists():
            chain.append(parent)
            if parent == parent.parent:
                break
            parent = parent.parent
        return list(reversed(chain))
