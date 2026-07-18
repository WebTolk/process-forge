#!/usr/bin/env python3
"""Cross-platform ProcessForge launcher."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def exec_args(args: list[str]) -> list[str]:
    if os.name != "nt":
        return args
    return [subprocess.list2cmdline([arg]) for arg in args]


def exec_processforge(cli: Path, argv: list[str]) -> int:
    args = exec_args([sys.executable, str(cli), *argv])
    if os.name == "nt":
        return os.spawnv(os.P_WAIT, sys.executable, args)
    os.execv(sys.executable, args)
    return 2


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[1]
    cli = root / "tools" / "processforge.py"
    if not cli.is_file():
        print(f"FAIL: ProcessForge CLI not found: {cli}", file=sys.stderr)
        return 1
    try:
        return exec_processforge(cli, argv)
    except OSError as exc:
        print("FAIL: could not exec ProcessForge CLI", file=sys.stderr)
        print(f"Reason: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
