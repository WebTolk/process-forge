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
CONTENT_PACK_ID = "processforge.official.content-workflow"
VERIFICATION_PACK_ID = "processforge.official.verification"
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


def run_pf_process(*args: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


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
        hints = before.get("inactive_classifier_hints", [])
        assert any(PACK_ID in hint for hint in hints), before

        processes = [
            run_pf_process("pack-activate", "--id", pack, "--workplace", str(workplace), "--apply")
            for pack in [PACK_ID, CONTENT_PACK_ID, VERIFICATION_PACK_ID]
        ]
        for process in processes:
            output, _stderr = process.communicate(timeout=120)
            assert process.returncode == 0, output
        registry = yaml.safe_load((workplace / "registries" / "process-packs.yaml").read_text(encoding="utf-8"))
        active_ids = {item.get("id") for item in registry.get("process_packs", [])}
        assert {PACK_ID, CONTENT_PACK_ID, VERIFICATION_PACK_ID}.issubset(active_ids), registry

        run_pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace))
        after = classification(project)
        assert after.get("status") == "classified", after
        assert "software.php-composer" in after.get("project_types", []), after
        assert CLASSIFIER_ID in after.get("loaded_classifiers", []), after
    print("PASS: smoke_official_pack_classifier_data_driven")


if __name__ == "__main__":
    main()
