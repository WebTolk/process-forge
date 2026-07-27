#!/usr/bin/env python3
"""Check generated process-authoring fixtures include evolve."""

from __future__ import annotations

from evolve_smoke_helpers import ROOT, load_yaml


def main() -> int:
    missing: list[str] = []
    for path in sorted((ROOT / "examples" / "process-authoring").rglob("answers.yaml")):
        if "evolve" not in load_yaml(path):
            missing.append(path.relative_to(ROOT).as_posix())
    for path in sorted((ROOT / "examples" / "process-authoring").rglob("process.yaml")):
        if "evolve" not in load_yaml(path):
            missing.append(path.relative_to(ROOT).as_posix())
    if missing:
        raise AssertionError("missing evolve fixtures: " + ", ".join(missing))
    print("PASS: generated process examples include evolve smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
