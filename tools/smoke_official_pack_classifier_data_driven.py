#!/usr/bin/env python3
"""Prove the official classifier affects a project only after pack activation."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "pf.py"
PACK_ID = "processforge.official.software-development"
CLASSIFIER_ID = "processforge.official.software-web.classifier"


def run_pf(*args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout + result.stderr


def classification(project: Path) -> dict:
    snapshot_path = project / ".pf" / "contexts" / "project-context.snapshot.yaml"
    snapshot = yaml.safe_load(snapshot_path.read_text(encoding="utf-8"))
    return snapshot.get("project_classification", {})


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-official-classifier-") as tmp:
        root = Path(tmp)
        workplace = root / "workplace"
        project = root / "project"
        project.mkdir()
        (project / "composer.json").write_text("{}\n", encoding="utf-8")

        run_pf("workplace-init", "--profile", "generic", "--workplace", str(workplace), "--apply")
        run_pf("project-init", "--project-root", str(project), "--workplace", str(workplace), "--apply")
        run_pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace))
        before = classification(project)
        assert before.get("status") == "unclassified", before
        assert before.get("project_types") in ([], ["unknown"]), before
        assert CLASSIFIER_ID not in before.get("loaded_classifiers", []), before

        run_pf("pack-activate", "--id", PACK_ID, "--workplace", str(workplace), "--apply")
        run_pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace))
        after = classification(project)
        assert after.get("status") == "classified", after
        assert "software.php-composer" in after.get("project_types", []), after
        assert CLASSIFIER_ID in after.get("loaded_classifiers", []), after
    print("PASS: smoke_official_pack_classifier_data_driven")


if __name__ == "__main__":
    main()
