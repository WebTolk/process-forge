"""Public release gates work from clean source and its packed archive."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load_module(
    "release_consumer_adapter", ROOT / "tools/smoke_release_project_validators.py"
)


class ConsumerFailures(unittest.TestCase):
    def test_setup_failure_stops_before_validation(self):
        with (
            mock.patch.object(
                adapter,
                "prepare_consumer",
                side_effect=subprocess.CalledProcessError(17, ["fixture"]),
            ),
            mock.patch.object(adapter, "run_step") as run,
        ):
            self.assertEqual(adapter.main(["--check", "doctor-project"]), 17)
            run.assert_not_called()

    def test_validation_failure_is_preserved(self):
        with (
            mock.patch.object(
                adapter, "prepare_consumer", return_value=Path("consumer")
            ),
            mock.patch.object(
                adapter,
                "run_step",
                side_effect=subprocess.CalledProcessError(19, ["validator"]),
            ),
        ):
            self.assertEqual(adapter.main(["--check", "events-validate"]), 19)


class PublicReleaseGates(unittest.TestCase):
    temporary: tempfile.TemporaryDirectory[str]
    base: Path
    source: Path
    extracted: Path
    env: dict[str, str]

    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="pf-release-gates-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.base = Path(cls.temporary.name).resolve()
        cls.source = cls.base / "source"
        cls.source.mkdir()
        cls.env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("PF_", "GIT_"))
        }
        cls.env["PYTHONDONTWRITEBYTECODE"] = "1"
        for key in (
            "LOCALAPPDATA",
            "XDG_CONFIG_HOME",
            "XDG_DATA_HOME",
            "XDG_CACHE_HOME",
            "TEMP",
            "TMP",
            "TMPDIR",
        ):
            target = cls.base / key.lower()
            target.mkdir()
            cls.env[key] = str(target)
        inventory = load_module(
            "release_gate_inventory", ROOT / "tools/validate-process-forge-checksums.py"
        )
        for name, path in inventory.public_file_entries(ROOT):
            target = cls.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(inventory.released_content(path))
        checksums = cls.source / "checksums/processforge.sha256"
        checksums.parent.mkdir(parents=True, exist_ok=True)
        checksums.write_bytes((ROOT / "checksums/processforge.sha256").read_bytes())
        assert not (cls.source / ".pf").exists()
        cls.run_cli(
            cls.source,
            "release-test",
            "--root",
            str(cls.source),
            "--public",
            "--no-clean",
            "--list",
        )
        assert not (cls.source / ".pf").exists(), "--list must not initialize or write"
        # The real packer requires committed Git provenance, even for a fixture.
        hooks = cls.base / "empty-hooks"
        hooks.mkdir()
        git = [
            "git",
            "-C",
            str(cls.source),
            "-c",
            f"core.hooksPath={hooks}",
            "-c",
            "commit.gpgSign=false",
            "-c",
            "user.name=Release fixture",
            "-c",
            "user.email=release-fixture@example.invalid",
        ]
        for args in (
            ["init"],
            ["add", "--all"],
            ["commit", "-m", "Public release fixture"],
        ):
            subprocess.run([*git, *args], env=cls.env, check=True, capture_output=True)
        archive = cls.base / "release.zip"
        cls.run_cli(
            cls.source,
            "release-pack",
            "--root",
            str(cls.source),
            "--output",
            str(archive),
        )
        cls.extracted = cls.base / "extracted"
        with zipfile.ZipFile(archive) as package:
            assert not any(name.startswith(".pf/") for name in package.namelist())
            package.extractall(cls.extracted)
        assert not (cls.extracted / ".pf").exists()

    @classmethod
    def run_cli(cls, root: Path, *args: str):
        result = subprocess.run(
            [sys.executable, str(root / "bin/pf.py"), *args],
            cwd=cls.base,
            env=cls.env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode:
            raise AssertionError(
                f"{args}: exit {result.returncode}\n{result.stdout}\n{result.stderr}"
            )
        return result

    def test_source_and_archive_independent_project_gates(self):
        for root in (self.source, self.extracted):
            inventory = (root / "checksums/processforge.sha256").read_bytes()
            for check in ("events-validate", "doctor-project"):
                with self.subTest(root=root.name, check=check):
                    result = self.run_cli(
                        root,
                        "release-test",
                        "--root",
                        str(root),
                        "--public",
                        "--no-clean",
                        "--only",
                        check,
                        "--fail-fast",
                    )
                    report = json.loads(
                        (
                            root / ".pf/runtime/release-test/latest-report.json"
                        ).read_text(encoding="utf8")
                    )
                    self.assertEqual(report["result"], "PASS")
                    self.assertTrue(report["public"])
                    self.assertEqual(len(report["checks"]), 1)
                    self.assertEqual(report["checks"][0]["label"], check)
                    self.assertEqual(report["checks"][0]["exit_code"], 0)
                    self.assertTrue(report["checks"][0]["public_gate"])
                    self.assertIn(
                        "smoke_release_project_validators.py",
                        report["checks"][0]["command"][1],
                    )
                    self.assertNotIn("RESULT: FAIL", result.stdout)
                    self.assertFalse((root / ".pf/process-forge.yaml").exists())
                    self.assertEqual(
                        (root / "checksums/processforge.sha256").read_bytes(), inventory
                    )

    def test_real_validators_reject_corrupt_consumer(self):
        original = adapter.prepare_consumer
        for check in ("events-validate", "doctor-project"):

            def corrupted(base, env):
                project = original(base, env)
                if check == "events-validate":
                    transcript = next(
                        (project / ".pf/runtime/chat/transcripts").glob("*.ndjson")
                    )
                    transcript.write_text("{broken\n", encoding="utf8")
                else:
                    (project / ".gitignore").unlink()
                return project

            with (
                self.subTest(check=check),
                mock.patch.object(adapter, "prepare_consumer", side_effect=corrupted),
            ):
                self.assertEqual(adapter.main(["--check", check]), 1)


if __name__ == "__main__":
    unittest.main()
