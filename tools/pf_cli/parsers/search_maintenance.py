"""Register the explicit workplace search-index maintenance command."""

from __future__ import annotations

import argparse
from collections.abc import Callable


def register_search_index_maintenance(
    add_parser: Callable[..., argparse.ArgumentParser],
    *,
    execute: Callable[[argparse.Namespace], int],
) -> None:
    """Register a supplied handler without constructing or running maintenance.

    Args:
        add_parser: Public parent subparser registration callback.
        execute: Explicitly composed workplace command handler.
    """
    parser = add_parser(
        "search-index-maintain",
        help="Explicitly maintain the workplace resource search index.",
        description=(
            "Workplace maintenance requires an explicit target and --apply. "
            "Project context and project Work do not authorize this operation."
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--workplace", required=True, help="Workplace root path.")
    parser.add_argument(
        "--apply", action="store_true", help="Authorize this explicit maintenance pass."
    )
    parser.add_argument("--json", action="store_true", help="Print one JSON report.")
    parser.set_defaults(func=execute)
