#!/usr/bin/env python3
"""Regression smoke for corrupt-registry preservation in PF-AUD-006."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "bin" / "pf.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PF), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def assert_refused_without_mutation(registry: Path, payload: bytes, workplace: Path) -> None:
    registry.write_bytes(payload)
    result = run(
        "tool-register",
        "--workplace",
        str(workplace),
        "--id",
        "audit-tool",
        "--capability",
        "audit",
        "--command",
        "python --version",
        "--apply",
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert registry.read_bytes() == payload, "corrupt registry was rewritten"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-remediation-registry-") as tmp:
        workplace = Path(tmp) / "workplace"
        initialized = run("workplace-init", "--workplace", str(workplace), "--apply")
        assert initialized.returncode == 0, initialized.stdout + initialized.stderr
        registry = workplace / "registries" / "tools.yaml"

        assert_refused_without_mutation(registry, b"tools: [unterminated\n", workplace)
        assert_refused_without_mutation(
            registry,
            b"schema_version: 1\ntools: {}\n",
            workplace,
        )

    print("PASS: registry safety regression smoke completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
