#!/usr/bin/env python3
"""Check built-in public stable processes declare evolve."""

from __future__ import annotations

import tempfile
from pathlib import Path

from evolve_smoke_helpers import ROOT, load_yaml, run_pf, write_yaml


def public_stable(data: dict) -> bool:
    catalog = data.get("catalog") if isinstance(data.get("catalog"), dict) else {}
    classification = str(catalog.get("classification") or ("PUBLIC_STABLE" if data.get("status") == "active" else "")).upper()
    public_surface = bool(catalog.get("public_surface", data.get("public_surface", True)))
    return classification == "PUBLIC_STABLE" and public_surface and data.get("status") == "active"


def main() -> int:
    missing: list[str] = []
    for path in sorted((ROOT / "processes" / "core").glob("*.yaml")):
        data = load_yaml(path)
        if not public_stable(data):
            continue
        evolve = data.get("evolve")
        if not isinstance(evolve, dict) or "enabled" not in evolve or "mode" not in evolve:
            missing.append(path.name)
        if isinstance(evolve, dict) and evolve.get("enabled") is False and not str(evolve.get("reason") or "").strip():
            missing.append(path.name + ": disabled reason")
    if missing:
        raise AssertionError("public stable processes missing explicit evolve: " + ", ".join(missing))

    with tempfile.TemporaryDirectory(prefix="pf-builtin-evolve-") as raw:
        root = Path(raw)
        (root / ".pf").mkdir(parents=True)
        (root / ".pf" / "process-forge.yaml").write_text("schema_version: 1\nprocess_forge: {}\nproject: {}\npaths: {}\npolicies: {}\n", encoding="utf-8")
        process = load_yaml(ROOT / "processes" / "core" / "bug-fix.yaml")
        process.pop("evolve", None)
        write_yaml(root / "processes" / "core" / "bug-fix.yaml", process)
        (root / "prompts").mkdir()
        (root / "prompts" / "bug-fix-agent.md").write_text("# Bug Fix Agent\n", encoding="utf-8")
        (root / "docs" / "processes").mkdir(parents=True)
        (root / "docs" / "processes" / "bug-fix.md").write_text("# Bug Fix\n", encoding="utf-8")
        (root / "examples" / "process-authoring" / "bug-fix").mkdir(parents=True)
        (root / "examples" / "process-authoring" / "bug-fix" / "README.md").write_text("# Bug Fix\n", encoding="utf-8")
        result = run_pf("builtin-process-catalog-doctor", "--root", str(root), "--public", expect=1)
        if "evolve" not in result.stdout:
            raise AssertionError("strict public doctor did not report missing evolve")
    print("PASS: built-in processes explicit evolve smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
