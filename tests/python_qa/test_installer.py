"""Verify managed-file backups and refusal of incompatible shared environments."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "shared_python_qa_install", ROOT / "tools/python-qa/install.py"
)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    """Keep preexisting managed files recoverable and reject incomplete installs."""

    def setUp(self):
        parent = Path(
            os.environ.get("PF_PYTHON_QA_TEST_ROOT", ROOT / ".pf/tmp/python-qa-tests")
        )
        parent.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="installer-", dir=parent)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source = ROOT / "tools/python-qa"
        self.destination = self.root / "shared tools"
        executable = (
            self.destination
            / ".venv"
            / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )
        executable.parent.mkdir(parents=True)
        executable.touch()
        self.info = subprocess.CompletedProcess(
            [], 0, json.dumps({"version": [3, 14], "executable": sys.executable})
        )

    def test_replaced_file_is_backed_up_and_reinstall_is_idempotent(self):
        previous = self.destination / "qa.py"
        previous.write_text("existing managed version", encoding="utf-8")
        with (
            patch.object(installer.subprocess, "run", return_value=self.info),
            patch.object(installer, "_run"),
        ):
            result = installer.install(self.source, self.destination, sys.executable)
            installer.install(self.source, self.destination, sys.executable)
        backups = list((self.destination / "backups").glob("*/qa.py"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(
            backups[0].read_text(encoding="utf-8"), "existing managed version"
        )
        self.assertEqual(result["python_version"], [3, 14])
        self.assertTrue((self.destination / "installed.json").is_file())

    def test_declared_other_version_is_refused_before_managed_files_change(self):
        (self.destination / "installed.json").write_text(
            '{"python_version":[3,12]}', encoding="utf-8"
        )
        with (
            patch.object(installer.subprocess, "run", return_value=self.info),
            patch.object(installer, "_run"),
        ):
            with self.assertRaisesRegex(ValueError, "different Python"):
                installer.install(self.source, self.destination, sys.executable)
        self.assertFalse((self.destination / "qa.py").exists())

    def test_existing_environment_with_wrong_version_is_refused(self):
        wrong = subprocess.CompletedProcess(
            [], 0, '{"version":[3,12],"executable":"other"}'
        )
        with (
            patch.object(installer.subprocess, "run", side_effect=[self.info, wrong]),
            patch.object(installer, "_run"),
        ):
            with self.assertRaisesRegex(ValueError, "another Python"):
                installer.install(self.source, self.destination, sys.executable)
        self.assertFalse((self.destination / "installed.json").exists())

    def test_failed_dependency_install_never_creates_success_receipt(self):
        with (
            patch.object(installer.subprocess, "run", return_value=self.info),
            patch.object(
                installer, "_run", side_effect=subprocess.CalledProcessError(1, ["pip"])
            ),
        ):
            with self.assertRaises(subprocess.CalledProcessError):
                installer.install(self.source, self.destination, sys.executable)
        self.assertFalse((self.destination / "installed.json").exists())


if __name__ == "__main__":
    unittest.main()
