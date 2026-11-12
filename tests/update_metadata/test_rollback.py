"""Package rollback restores selected registry metadata through real CLI."""

from __future__ import annotations

import argparse
import copy
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src")]
import processforge as cli  # noqa: E402 -- capture entry before Core imports
from update_smoke_helpers import first_candidate_id, make_update_fixture  # noqa: E402

from processforge_core.maintenance import update_metadata  # noqa: E402


class RollbackMetadata(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="pf-metadata-rollback-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.env = {
            k: v for k, v in os.environ.items() if not k.startswith(("PF_", "GIT_"))
        }
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"
        for key in (
            "LOCALAPPDATA",
            "APPDATA",
            "XDG_CONFIG_HOME",
            "XDG_DATA_HOME",
            "XDG_CACHE_HOME",
            "TEMP",
            "TMP",
            "TMPDIR",
        ):
            target = self.base / key.lower()
            target.mkdir()
            self.env[key] = str(target)

    def run_pf(self, workplace: Path, *args: str, ok: bool = True):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "bin/pf.py"),
                "update",
                *args,
                "--workplace",
                str(workplace),
            ],
            cwd=self.base,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def fixture(self, name: str, tool: bool = False):
        workplace = self.base / name
        spec = make_update_fixture(workplace, tool=tool)
        registry = workplace / "registries/installed-subjects.yaml"
        data = yaml.safe_load(registry.read_text())
        data["opaque"] = {"preserve": ["Привет", None, 7]}
        data["subjects"][0]["custom"] = {"installed_by": "operator"}
        other = {
            "type": spec["subject_type"],
            "id": "unrelated",
            "version": "9.0.0",
            "custom": ["keep"],
        }
        data["subjects"].append(other)
        registry.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf8")
        self.run_pf(workplace, "candidates", "refresh")
        candidate = first_candidate_id(workplace)
        self.run_pf(workplace, "stage", "--candidate", candidate)
        payload = workplace / (
            "tools/local-linter.py"
            if tool
            else "packages/acme.software-processes/package.yaml"
        )
        return workplace, registry, candidate, payload, copy.deepcopy(data)

    def apply(self, workplace, candidate):
        return self.run_pf(workplace, "apply", "--candidate", candidate, "--confirm")

    def rollback(self, workplace, candidate, ok=True):
        return self.run_pf(workplace, "rollback", "--candidate", candidate, ok=ok)

    def test_file_and_tree_restore_exact_selected_record_and_reoffer(self):
        for tool in (False, True):
            with self.subTest(tool=tool):
                workplace, registry, candidate, payload, before = self.fixture(
                    str(tool), tool
                )
                old_payload = payload.read_bytes()
                self.apply(workplace, candidate)
                applied = yaml.safe_load(registry.read_text())
                self.assertEqual(applied["subjects"][0]["version"], "1.1.0")
                applied["subjects"][1]["version"] = "10.0.0"
                applied["new_foreign_field"] = "preserve"
                registry.write_text(yaml.safe_dump(applied), encoding="utf8")
                self.rollback(workplace, candidate)
                restored = yaml.safe_load(registry.read_text())
                self.assertEqual(restored["subjects"][0], before["subjects"][0])
                self.assertEqual(restored["subjects"][1], applied["subjects"][1])
                self.assertEqual(restored["opaque"], before["opaque"])
                self.assertEqual(restored["new_foreign_field"], "preserve")
                self.assertEqual(payload.read_bytes(), old_payload)
                self.rollback(workplace, candidate)
                self.assertEqual(payload.read_bytes(), old_payload)
                self.run_pf(workplace, "entity-sources", "rebuild")
                self.run_pf(workplace, "candidates", "refresh")
                self.assertEqual(first_candidate_id(workplace), candidate)
                self.apply(workplace, candidate)
                self.rollback(workplace, candidate)
                self.assertEqual(
                    yaml.safe_load(registry.read_text())["subjects"][0],
                    before["subjects"][0],
                )

    def test_prior_absent_record_is_removed_without_other_changes(self):
        for tool in (False, True):
            with self.subTest(tool=tool):
                workplace, registry, candidate, _, before = self.fixture(
                    "absent" + str(tool), tool
                )
                before["subjects"].pop(0)
                registry.write_text(yaml.safe_dump(before), encoding="utf8")
                self.apply(workplace, candidate)
                self.rollback(workplace, candidate)
                after = yaml.safe_load(registry.read_text())
                self.assertEqual(after["subjects"], before["subjects"])
                self.assertEqual(after["opaque"], before["opaque"])

    def test_drift_refuses_before_payload_restore_and_repeat_apply_keeps_backup(self):
        workplace, registry, candidate, payload, _ = self.fixture("drift")
        self.apply(workplace, candidate)
        backup = (
            workplace / "runtime/update/backups" / candidate / "installed-subject.yaml"
        )
        original_backup = backup.read_bytes()
        self.run_pf(workplace, "apply", "--candidate", candidate, "--confirm", ok=False)
        self.assertEqual(backup.read_bytes(), original_backup)
        installed = payload.read_bytes()
        data = yaml.safe_load(registry.read_text())
        data["subjects"][0]["custom"] = "new writer"
        registry.write_text(yaml.safe_dump(data), encoding="utf8")
        result = self.rollback(workplace, candidate, ok=False)
        self.assertIn("installed_subject_changed", result.stdout)
        self.assertEqual(payload.read_bytes(), installed)
        self.assertEqual(yaml.safe_load(registry.read_text()), data)

    def test_duplicate_selected_subject_refuses_before_apply(self):
        workplace, registry, candidate, payload, before = self.fixture("duplicate")
        before["subjects"].append(copy.deepcopy(before["subjects"][0]))
        registry.write_text(yaml.safe_dump(before), encoding="utf8")
        old_payload = payload.read_bytes()
        result = self.run_pf(
            workplace, "apply", "--candidate", candidate, "--confirm", ok=False
        )
        self.assertIn("installed_subject_ambiguous", result.stdout)
        self.assertEqual(payload.read_bytes(), old_payload)
        self.assertEqual(yaml.safe_load(registry.read_text()), before)
        self.assertFalse((workplace / "runtime/update/backups" / candidate).exists())

    def test_missing_payload_backup_does_not_revert_registry_then_retry(self):
        workplace, registry, candidate, payload, before = self.fixture(
            "missing-backup", True
        )
        self.apply(workplace, candidate)
        applied = registry.read_bytes()
        backup = workplace / "runtime/update/backups" / candidate / "previous-file"
        hidden = backup.with_name("held-previous-file")
        backup.rename(hidden)
        self.rollback(workplace, candidate, ok=False)
        self.assertEqual(registry.read_bytes(), applied)
        hidden.rename(backup)
        self.rollback(workplace, candidate)
        self.assertEqual(
            yaml.safe_load(registry.read_text())["subjects"][0], before["subjects"][0]
        )

    def test_failed_metadata_apply_keeps_preimage_for_rollback(self):
        workplace, registry, candidate, payload, before = self.fixture("failed-apply")
        old_payload = payload.read_bytes()
        original_write = update_metadata._write

        def fail_registry(path, value):
            if path == registry:
                raise OSError("injected registry publication failure")
            return original_write(path, value)

        args = argparse.Namespace(
            workplace=str(workplace),
            candidate=candidate,
            confirm=True,
            dry_run=False,
            allow_custom_command=False,
        )
        with mock.patch.object(update_metadata, "_write", side_effect=fail_registry):
            self.assertEqual(cli.command_update_apply(args), 1)
        self.assertEqual(yaml.safe_load(registry.read_text()), before)
        self.rollback(workplace, candidate)
        self.assertEqual(payload.read_bytes(), old_payload)
        self.assertEqual(
            yaml.safe_load(registry.read_text())["subjects"][0], before["subjects"][0]
        )

    def test_failed_metadata_restore_can_be_retried(self):
        workplace, registry, candidate, payload, before = self.fixture("failed-restore")
        old_payload = payload.read_bytes()
        self.apply(workplace, candidate)
        applied = registry.read_bytes()
        original_write = update_metadata._write

        def fail_registry(path, value):
            if path == registry:
                raise OSError("injected registry restore failure")
            return original_write(path, value)

        with mock.patch.object(update_metadata, "_write", side_effect=fail_registry):
            self.assertEqual(
                cli.command_update_rollback(
                    argparse.Namespace(workplace=str(workplace), candidate=candidate)
                ),
                1,
            )
        self.assertEqual(registry.read_bytes(), applied)
        self.assertEqual(payload.read_bytes(), old_payload)
        self.rollback(workplace, candidate)
        self.assertEqual(
            yaml.safe_load(registry.read_text())["subjects"][0], before["subjects"][0]
        )

    def test_missing_or_mismatched_metadata_preimage_refuses(self):
        workplace, registry, candidate, payload, _ = self.fixture("preimage")
        self.apply(workplace, candidate)
        metadata = (
            workplace / "runtime/update/backups" / candidate / "installed-subject.yaml"
        )
        original = metadata.read_bytes()
        installed = payload.read_bytes()
        document = yaml.safe_load(metadata.read_text(encoding="utf8"))
        document["install_path"] = str(workplace / "foreign")
        metadata.write_text(yaml.safe_dump(document), encoding="utf8")
        self.assertIn(
            "preimage_mismatch", self.rollback(workplace, candidate, ok=False).stdout
        )
        self.assertEqual(payload.read_bytes(), installed)
        metadata.unlink()
        self.assertIn(
            "preimage_missing", self.rollback(workplace, candidate, ok=False).stdout
        )
        self.assertEqual(payload.read_bytes(), installed)
        metadata.write_bytes(original)
        self.rollback(workplace, candidate)

    def test_applied_phase_write_failure_keeps_recoverable_metadata(self):
        workplace, registry, candidate, payload, before = self.fixture("phase")
        old_payload = payload.read_bytes()
        original_write = update_metadata._write

        def fail_phase(path, value):
            if (
                path.name == "installed-subject.yaml"
                and value.get("phase") == "applied"
            ):
                raise OSError("injected phase publication failure")
            return original_write(path, value)

        args = argparse.Namespace(
            workplace=str(workplace),
            candidate=candidate,
            confirm=True,
            dry_run=False,
            allow_custom_command=False,
        )
        with mock.patch.object(update_metadata, "_write", side_effect=fail_phase):
            self.assertEqual(cli.command_update_apply(args), 1)
        self.assertEqual(
            yaml.safe_load(registry.read_text())["subjects"][0]["version"], "1.1.0"
        )
        self.rollback(workplace, candidate)
        self.assertEqual(payload.read_bytes(), old_payload)
        self.assertEqual(
            yaml.safe_load(registry.read_text())["subjects"][0], before["subjects"][0]
        )


if __name__ == "__main__":
    unittest.main()
