"""Register the explicit knowledge batch command with a supplied handler."""

from __future__ import annotations

import argparse
from collections.abc import Callable


def register_knowledge_add_batch(
    add_parser: Callable[..., argparse.ArgumentParser],
    *,
    execute: Callable[[argparse.Namespace], int],
) -> None:
    """Register a read-only default and optional explicit application mode."""
    parser = add_parser(
        "knowledge-add-batch",
        help="Preview or apply YAML resource records to an existing knowledge package.",
        allow_abbrev=False,
    )
    parser.add_argument("--workplace", required=True, help="Workplace root path.")
    parser.add_argument(
        "--package", required=True, help="Existing knowledge package id."
    )
    parser.add_argument(
        "--batch-file", required=True, help="Schema 1 YAML resource batch."
    )
    parser.add_argument("--package-root", help="Package root id from the registry.")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true", help="Commit each valid record.")
    modes.add_argument(
        "--dry-run", action="store_true", help="Preview without writing."
    )
    parser.add_argument("--json", action="store_true", help="Print one JSON report.")
    parser.set_defaults(func=execute)
