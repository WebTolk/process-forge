"""Exercise update discovery through the public ProcessForge CLI."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from tools.update_smoke_helpers import make_package_zip, sha256, write_json, write_yaml

ROOT = Path(__file__).resolve().parents[2]
SUBJECT_ID = "acme.software-processes"
SUBJECT_TYPE = "process_package"
SOURCE_ID = "acme-main"
SITE_ID = f"{SUBJECT_TYPE}:{SUBJECT_ID}:{SOURCE_ID}"
MANIFEST = Path("updates/manifest.json")
CHANGELOG = Path("updates/CHANGELOG.md")
DERIVED_SITES = Path("runtime/update/installed-update-sites.json")
CANDIDATES = Path("runtime/update/candidates.json")
NOTIFICATIONS = Path("runtime/update/notifications.json")
INBOX_ENTRY = Path("director/inbox/existing.txt")


def _make_workplace(
    workplace: Path,
    *,
    source_policy: Mapping[str, str | bool] | None = None,
    installed_policy: Mapping[str, str | bool] | None = None,
    channel: str = "stable",
) -> None:
    install_path = f"packages/{SUBJECT_ID}"
    policy = {
        "notify_operator": True,
        "notify_director_inbox": True,
        "install_path": install_path,
        **(source_policy or {}),
    }
    local_policy = {"mode": "manual", **(installed_policy or {})}
    source_settings = "\n".join(
        f"      {key}: {json.dumps(value)}" for key, value in policy.items()
    )
    installed_settings = "\n".join(
        f"      {key}: {json.dumps(value)}" for key, value in local_policy.items()
    )
    write_yaml(
        workplace / install_path / "package.yaml",
        f"""
id: {SUBJECT_ID}
type: {SUBJECT_TYPE}
version: 1.0.0
update_sites:
  - id: {SOURCE_ID}
    enabled: true
    manifest_url: "{(workplace / MANIFEST).as_uri()}"
    changelog_url: "{(workplace / CHANGELOG).as_uri()}"
    channel: {channel}
    trust:
      require_https: false
      require_sha256: true
      allow_unsigned: true
      signature_required: false
    policy:
{source_settings}
""",
    )
    write_yaml(
        workplace / "registries" / "installed-subjects.yaml",
        f"""
schema_version: 1
subjects:
  - id: {SUBJECT_ID}
    type: {SUBJECT_TYPE}
    scope: global
    version: 1.0.0
    install_path: {install_path}
    update_policy:
{installed_settings}
""",
    )
    write_yaml(workplace / CHANGELOG, "# Fixture changelog")
    write_json(workplace / NOTIFICATIONS, {"schema_version": 1, "notifications": []})
    write_yaml(workplace / INBOX_ENTRY, "Existing director inbox entry.")


def _release(
    workplace: Path, version: str, *, subject_id: str = SUBJECT_ID
) -> dict[str, str]:
    artifact = workplace / "updates" / f"{subject_id}-{version}.zip"
    digest = make_package_zip(
        artifact, subject_id=subject_id, subject_type=SUBJECT_TYPE, version=version
    )
    return {"version": version, "download_url": artifact.as_uri(), "sha256": digest}


def _subject_release(
    workplace: Path, subject_id: str, version: str, channel: str
) -> dict[str, Any]:
    release = _release(workplace, version, subject_id=subject_id)
    return {
        "version": version,
        "channels": [channel],
        "artifacts": [{"url": release["download_url"], "sha256": release["sha256"]}],
    }


def _write_stable_manifest(workplace: Path, *releases: dict[str, Any]) -> None:
    write_json(
        workplace / MANIFEST,
        {
            "schema_version": 1,
            "kind": "processforge.update_manifest",
            "subject": {"id": SUBJECT_ID, "type": SUBJECT_TYPE},
            "channels": {"stable": {"versions": list(releases)}},
        },
    )


def _file_hashes(workplace: Path) -> dict[str, str]:
    return {
        path.relative_to(workplace).as_posix(): sha256(path)
        for path in workplace.rglob("*")
        if path.is_file()
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class UpdateCandidateDiscoveryTests(unittest.TestCase):
    def _workplace(self) -> Path:
        directory = tempfile.TemporaryDirectory(prefix="pf-update-discovery-")
        self.addCleanup(directory.cleanup)
        return Path(directory.name).resolve()

    def _refresh(self, workplace: Path, *, dry_run: bool) -> str:
        command = [
            sys.executable,
            "-B",
            "bin/pf.py",
            "update",
            "candidates",
            "refresh",
            "--workplace",
            str(workplace),
            "--channel",
            "stable",
        ]
        if dry_run:
            command.append("--dry-run")
        result = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, timeout=60, check=False
        )
        self.assertEqual(result.returncode, 0, f"{result.stdout}\n{result.stderr}")
        self.assertEqual(result.stderr, "")
        return result.stdout

    def _dry_run(self, workplace: Path) -> dict[str, Any]:
        before = _file_hashes(workplace)
        stdout = self._refresh(workplace, dry_run=True)
        self.assertEqual(_file_hashes(workplace), before)
        payload = json.loads(stdout)
        self.assertEqual(
            set(payload),
            {"schema_version", "generated_at", "channel", "candidates", "conflicts"},
        )
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["channel"], "stable")
        self.assertIsInstance(payload["generated_at"], str)
        return payload

    def _candidate(
        self, payload: dict[str, Any], version: str, *, channel: str = "stable"
    ) -> dict[str, Any]:
        self.assertEqual(payload["conflicts"], [])
        self.assertEqual(len(payload["candidates"]), 1)
        candidate = payload["candidates"][0]
        self.assertEqual(candidate["site_id"], SITE_ID)
        self.assertEqual(candidate["source_id"], SOURCE_ID)
        self.assertEqual(
            candidate["subject"],
            {"id": SUBJECT_ID, "type": SUBJECT_TYPE, "scope": "global"},
        )
        self.assertEqual(candidate["installed_version"], "1.0.0")
        self.assertEqual(candidate["available_version"], version)
        self.assertEqual(candidate["channel"], channel)
        return candidate

    def test_uses_highest_release_allowed_by_policy(self) -> None:
        scenarios = (
            ("major", {"allow_major": False}, ("1.1.0", "2.0.0"), "1.1.0", None),
            ("pin", {"pin_version": "1.1.0"}, ("1.1.0", "2.0.0"), "1.1.0", None),
            (
                "matching-pin-blocked-by-major",
                {"pin_version": "2.0.0", "allow_major": False},
                ("1.1.0", "2.0.0"),
                None,
                "candidate 2.0.0 blocked by allow_major=false",
            ),
            (
                "pin-conflict-takes-precedence",
                {"pin_version": "1.9.0", "allow_major": False},
                ("1.1.0", "2.0.0"),
                None,
                "candidate 2.0.0 blocked by pin_version 1.9.0",
            ),
            (
                "no-newer-release",
                {"pin_version": "1.9.0", "allow_major": False},
                ("0.9.0", "1.0.0"),
                None,
                None,
            ),
        )
        for label, policy, releases, expected_version, reason in scenarios:
            with self.subTest(scenario=label):
                workplace = self._workplace()
                _make_workplace(workplace, source_policy=policy)
                _write_stable_manifest(
                    workplace, *(_release(workplace, version) for version in releases)
                )
                payload = self._dry_run(workplace)
                if expected_version:
                    self._candidate(payload, expected_version)
                else:
                    self.assertEqual(payload["candidates"], [])
                    expected_conflicts = (
                        [{"site_id": SITE_ID, "reason": reason}] if reason else []
                    )
                    self.assertEqual(payload["conflicts"], expected_conflicts)

    def test_installed_policy_overrides_source_policy(self) -> None:
        workplace = self._workplace()
        _make_workplace(
            workplace,
            source_policy={"allow_major": False},
            installed_policy={"allow_major": True},
        )
        _write_stable_manifest(
            workplace, _release(workplace, "1.1.0"), _release(workplace, "2.0.0")
        )
        candidate = self._candidate(self._dry_run(workplace), "2.0.0")
        self.assertIs(candidate["update_policy"]["allow_major"], True)

    def test_source_channel_and_subject_filter_manifest_versions(self) -> None:
        workplace = self._workplace()
        _make_workplace(workplace, channel="beta")
        other_id = "acme.other-package"
        write_json(
            workplace / MANIFEST,
            {
                "schema_version": 1,
                "kind": "processforge.update_manifest",
                "subjects": [
                    {
                        "id": other_id,
                        "type": SUBJECT_TYPE,
                        "versions": [
                            _subject_release(workplace, other_id, "3.0.0", "beta")
                        ],
                    },
                    {
                        "id": SUBJECT_ID,
                        "type": SUBJECT_TYPE,
                        "versions": [
                            _subject_release(workplace, SUBJECT_ID, "1.1.0", "beta"),
                            _subject_release(workplace, SUBJECT_ID, "2.0.0", "stable"),
                        ],
                    },
                ],
            },
        )
        self._candidate(self._dry_run(workplace), "1.1.0", channel="beta")

    def test_missing_local_manifest_reports_site_conflict(self) -> None:
        workplace = self._workplace()
        _make_workplace(workplace)
        payload = self._dry_run(workplace)
        self.assertEqual(payload["candidates"], [])
        self.assertEqual(len(payload["conflicts"]), 1)
        conflict = payload["conflicts"][0]
        self.assertEqual(set(conflict), {"site_id", "reason"})
        self.assertEqual(conflict["site_id"], SITE_ID)
        self.assertRegex(conflict["reason"], r"(?i)manifest|no such file|not found")

    def test_missing_required_hash_leaves_candidate_visible(self) -> None:
        workplace = self._workplace()
        _make_workplace(workplace)
        release = _release(workplace, "1.1.0")
        del release["sha256"]
        _write_stable_manifest(workplace, release)
        candidate = self._candidate(self._dry_run(workplace), "1.1.0")
        self.assertEqual(candidate["download_url"], release["download_url"])
        self.assertIsNone(candidate["sha256"])
        self.assertIsNone(candidate["artifact_sha256"])
        self.assertEqual(candidate["status"], "missing_required_hash")
        self.assertIs(candidate["installable"], False)
        self.assertEqual(candidate["reason"], "sha256 required before stage/apply")

    def test_refresh_persists_derived_sites_cache_and_notifications(self) -> None:
        workplace = self._workplace()
        _make_workplace(workplace)
        release = {
            **_release(workplace, "1.1.0"),
            "breaking": True,
            "migration_required": True,
        }
        _write_stable_manifest(workplace, release)
        expected = self._dry_run(workplace)
        candidate = self._candidate(expected, "1.1.0")
        self.assertEqual(candidate["status"], "available")
        self.assertIs(candidate["installable"], True)
        self.assertEqual(candidate["sha256"], release["sha256"])

        before = _file_hashes(workplace)
        stdout = self._refresh(workplace, dry_run=False)
        self.assertEqual(
            stdout.splitlines(),
            [
                "CANDIDATES: 1",
                f"TARGET: {CANDIDATES.as_posix()}",
                f"NOTIFICATIONS: {NOTIFICATIONS.as_posix()}",
            ],
        )
        cache = _read_json(workplace / CANDIDATES)
        self.assertIsInstance(cache["generated_at"], str)
        self.assertEqual({**cache, "generated_at": expected["generated_at"]}, expected)

        after = _file_hashes(workplace)
        derived_sites = _read_json(workplace / DERIVED_SITES)["sites"]
        self.assertEqual(len(derived_sites), 1)
        site = derived_sites[0]
        self.assertEqual(site["site_id"], SITE_ID)
        self.assertIs(site["enabled"], True)
        self.assertEqual(
            site["source"]["manifest_url"], (workplace / MANIFEST).as_uri()
        )

        self.assertNotEqual(
            after[NOTIFICATIONS.as_posix()], before[NOTIFICATIONS.as_posix()]
        )
        notifications = _read_json(workplace / NOTIFICATIONS)["notifications"]
        self.assertEqual(len(notifications), 1)
        notification = notifications[0]
        self.assertEqual(notification["candidate_id"], candidate["id"])
        self.assertEqual(notification["available_version"], "1.1.0")
        self.assertEqual(after[INBOX_ENTRY.as_posix()], before[INBOX_ENTRY.as_posix()])
        director_entries = [
            _read_json(workplace / name)
            for name in (after.keys() - before.keys())
            if name.startswith("director/inbox/")
        ]
        self.assertEqual(director_entries, [notification])
