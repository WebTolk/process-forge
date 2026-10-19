#!/usr/bin/env python3
"""Regression smoke for the public release distribution-artifact gate."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import processforge


def failures(root: Path) -> list[str]:
    return [item.message for item in processforge.public_release_checks(root) if item.level == "FAIL"]


def main() -> int:
    accepted = (
        "On Windows PowerShell:\n\n```powershell\npython bin/pf.py version\n```",
        "В Windows PowerShell:\n\n```powershell\npython bin/pf.py version\n```",
        "The CLI does not require PF Runtime,\nPowerShell or Git.",
        "Файловый режим не требует PF Runtime,\nPowerShell или Git.",
        "Node.js, PHP or PowerShell is not a general CLI dependency.",
        "Node.js, PHP и PowerShell не являются общими зависимостями CLI.",
        "Invoke Python directly without activating\nPowerShell scripts or changing execution policy.",
        "Вызывайте Python напрямую, без активации сценариев\nPowerShell и изменения политики исполнения.",
    )
    rejected = (
        "Run install.ps1",
        "PowerShell is not required, but run legacy.PS1",
        "Run tools/setup.ps1 --apply",
        "[Legacy installer](install.Ps1)",
        "```powershell\npowershell -File install.ps1\n```",
    )
    for text in accepted:
        from processforge_core.maintenance.release_sources import ReleaseSourcePolicy

        assert not ReleaseSourcePolicy().forbidden_powershell_reference(text), text
    for text in rejected:
        from processforge_core.maintenance.release_sources import ReleaseSourcePolicy

        assert ReleaseSourcePolicy().forbidden_powershell_reference(text), text
    for name in ("getting-started/installation.md", "known-limitations.md", "requirements.md"):
        for language in ("", "ru"):
            path = ROOT / "docs" / language / name
            from processforge_core.maintenance.release_sources import ReleaseSourcePolicy

            assert not ReleaseSourcePolicy().forbidden_powershell_reference(path.read_text(encoding="utf-8")), path
    with tempfile.TemporaryDirectory(prefix="pf-public-dist-") as raw:
        root = Path(raw)
        (root / "VERSION").write_text("1.1.0\n", encoding="utf-8")
        dist = root / "dist"
        dist.mkdir()
        for name in ("processforge-1.1.0.zip", "processforge-1.1.0.manifest.json"):
            (dist / name).write_text("current", encoding="utf-8")
        assert not failures(root), failures(root)
        (dist / "processforge-1.0.9.zip").write_text("stale", encoding="utf-8")
        assert any("processforge-1.0.9.zip" in message for message in failures(root)), failures(root)
    print("PASS: public gate accepts current EN/RU Python guidance, rejects wrappers and stale dist artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
