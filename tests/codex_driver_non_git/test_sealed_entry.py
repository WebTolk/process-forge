"""The registered Codex wrapper is an exact sealed entry on each real OS."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pf_native_control as native
import pytest

SOURCE = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "entry", ["valid", *(["tampered", "foreign"] if os.name == "posix" else [])]
)
def test_sealed_codex_entry_keeps_origin_authentication(tmp_path: Path, entry: str):
    spec = importlib.util.spec_from_file_location(
        "codex_entry_inventory", SOURCE / "tools/validate-process-forge-checksums.py"
    )
    assert spec is not None and spec.loader is not None
    inventory = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inventory)
    payload = {
        name: inventory.released_content(path)
        for name, path in inventory.public_file_entries(SOURCE)
    }
    payload[native.INVENTORY] = b""
    publication = native.build_publication(
        payload,
        version=(SOURCE / "VERSION").read_text().strip(),
        source={"fixture": True},
        generated_at="fixture",
    )
    root = tmp_path / "publication"
    for name, raw in {
        **publication.payload,
        native.MANIFEST: publication.manifest,
    }.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    script = root / "tools/codex_exec_worker.py"
    if entry == "tampered":
        raw = script.read_bytes()
        changed = raw.replace(b"--skip-git-repo-check", b"--skip-git-repo-checl", 1)
        assert changed != raw and len(changed) == len(raw)
        script.write_bytes(changed)
    elif entry == "foreign":
        foreign = script.with_name("foreign_helper.py")
        foreign.write_bytes(script.read_bytes())
        script = foreign
    result = subprocess.run(
        [sys.executable, "-B", str(script), "--help"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    if entry == "valid":
        assert result.returncode == 0, result.stderr
        assert "--worker-prompt" in result.stdout
    else:
        assert result.returncode != 0
        assert "NativeControlError" in result.stderr
