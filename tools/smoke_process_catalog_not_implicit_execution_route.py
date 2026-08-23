"""Smoke test that manifest process catalogs do not imply an execution route."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str, cwd: Path = ROOT, expected_codes: set[int] | None = None) -> str:
    expected_codes = expected_codes or {0}
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "processforge.py"), *args],
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if result.returncode not in expected_codes:
        raise AssertionError(result.stdout + result.stderr)
    return result.stdout


def context_check(project: Path, workplace: Path, *, expected_codes: set[int] | None = None) -> dict:
    return json.loads(
        run_cli(
            "project-context-check",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--json",
            expected_codes=expected_codes,
        )
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-process-catalog-smoke-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        project.mkdir()

        run_cli("workplace-init", "--workplace", str(workplace), "--apply")
        run_cli(
            "project-onboard",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--type",
            "generic",
            "--apply",
        )

        process_dir = project / ".pf" / "processes"
        process_dir.mkdir(parents=True, exist_ok=True)
        (process_dir / "needs-fixture-capability.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "id": "needs-fixture-capability",
                    "name": "Needs Fixture Capability",
                    "version": "1.0.0",
                    "status": "active",
                    "required_capabilities": ["fixture.capability"],
                    "stages": [],
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        manifest_path = project / ".pf" / "process-forge.yaml"
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest["process"] = ""
        manifest["processes"] = [
            {
                "id": "needs-fixture-capability",
                "path": "processes/needs-fixture-capability.yaml",
            }
        ]
        manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")

        run_cli(
            "project-context-refresh",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--apply",
        )
        catalog_only = context_check(project, workplace)
        assert catalog_only["status"] == "fresh", catalog_only
        assert catalog_only["execution_readiness"]["status"] == "ready", catalog_only
        snapshot = yaml.safe_load((project / ".pf" / "contexts" / "project-context.snapshot.yaml").read_text(encoding="utf-8"))
        resolved_context = snapshot["resolved_context"]
        assert resolved_context["process"] == "", resolved_context
        assert resolved_context["execution_route"]["process"] == "", resolved_context
        assert not resolved_context["capability_resolution"]["unsatisfied"], resolved_context

        manifest["process"] = "needs-fixture-capability"
        manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
        run_cli(
            "project-context-refresh",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--apply",
            expected_codes={0, 1},
        )
        explicit_process = context_check(project, workplace, expected_codes={0, 1})
        assert explicit_process["status"] == "broken", explicit_process
        assert explicit_process["execution_readiness"]["status"] == "blocked", explicit_process
        missing = explicit_process["execution_readiness"]["missing_capabilities"]
        assert missing and missing[0]["capability"] == "fixture.capability", explicit_process

    print("PASS: manifest process catalogs do not imply execution routes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
