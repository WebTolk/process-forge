#!/usr/bin/env python3
"""ProcessForge Server operator launcher using the standard PF CLI."""
import sys
from pf import main

if __name__ == "__main__":
    raise SystemExit(main(["server", *sys.argv[1:]]))
