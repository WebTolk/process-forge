#!/usr/bin/env python3
"""Fail if runtime logic hardcodes real product specialization/resource IDs."""

from __future__ import annotations

from specialization_smoke_helpers import ROOT


FORBIDDEN = [
    "docs." + "php",
    "docs." + "joomla",
    "docs." + "joomshopping",
    "x" + "debug",
    "screaming" + "-frog",
    "platform." + "joomla-backend",
    "platform." + "joomshopping-content",
    "specialization." + "backend-development",
    "specialization." + "content-management",
]


def main() -> None:
    runtime = (ROOT / "tools" / "processforge.py").read_text(encoding="utf-8", errors="replace").lower()
    found = [item for item in FORBIDDEN if item in runtime]
    if found:
        raise AssertionError("forbidden runtime ids: " + ", ".join(found))
    print("PASS: smoke_specialization_no_core_id_hardcode")


if __name__ == "__main__":
    main()
