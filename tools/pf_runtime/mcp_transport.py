"""Small stdlib-only transport helpers shared by MCP entry processes."""

from __future__ import annotations

import codecs
import sys


def configure_utf8() -> None:
    """Configure owned text codecs without replacing borrowed streams."""
    for stream in (sys.stdin, sys.stdout):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        encoding = getattr(stream, "encoding", None)
        if isinstance(encoding, str):
            try:
                if codecs.lookup(encoding).name == "utf-8":
                    continue
            except LookupError:
                pass
        reconfigure(encoding="utf-8", errors=getattr(stream, "errors", None))
