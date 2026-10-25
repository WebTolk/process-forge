#!/usr/bin/env python3
"""ProcessForge Server operator launcher using the standard PF CLI."""

import sys
from pathlib import Path
from runpy import run_path

# Execute the adjacent source directly; importing pf can trust unchecked pyc.
main = run_path(str(Path(__file__).resolve().with_name("pf.py")), run_name="pf")["main"]

if __name__ == "__main__":
    raise SystemExit(main(["server", *sys.argv[1:]]))
