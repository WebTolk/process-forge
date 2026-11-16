#!/usr/bin/env python3
"""Qualify public 1.2.0 Core files and record separate project migration limits."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform as host_info
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

PUBLIC_COMMIT = "b70df739700f1559570f4b65481cd39616ccc1ea"
PUBLIC_ZIP_SHA256 = "0cd5c1f48ca0e94ddf5b0298b774a3498baf20e5a64b84dd9c05bbc0f36a2880"
PUBLIC_SIDECAR_SHA256 = (
    "2881c62ff279c9d418d7bb88ad01a321817c1c7454ec03e10227d3f6791d40bd"
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def verify_archive(
    archive: Path, sidecar: Path, expected_sha256: str, expected_commit: str
) -> dict[str, Any]:
    raw = archive.read_bytes()
    metadata = json.loads(sidecar.read_bytes())
    assert sha256(raw) == expected_sha256, "archive hash differs from selected input"
    assert metadata["archive"]["sha256"] == expected_sha256
    assert metadata["archive"]["size"] == len(raw)
    assert metadata["source"]["commit"] == expected_commit
    assert metadata["source"]["dirty"] is False
    with zipfile.ZipFile(archive) as bundle:
        expected = {row["path"]: row for row in metadata["files"]}
        assert len(bundle.namelist()) == len(set(bundle.namelist()))
        assert set(bundle.namelist()) == set(expected)
        for name, row in expected.items():
            assert not name.startswith(("/", "\\")) and "\\" not in name
            assert all(
                part not in ("", ".", "..") and ":" not in part
                for part in name.split("/")
            )
            assert (
                not ((bundle.getinfo(name).external_attr >> 16) & 0o170000) == 0o120000
            )
            content = bundle.read(name)
            assert len(content) == row["size"] and sha256(content) == row["sha256"]
    return metadata


def snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256(path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def main() -> int:
    parser = argparse.ArgumentParser(__doc__)
    for name in ("public-dir", "candidate", "sidecar", "root", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    assert not root.exists() and not out.exists(), (
        "use new owned fixture/evidence roots"
    )
    public = args.public_dir.resolve()
    archive, sidecar = args.candidate.resolve(), args.sidecar.resolve()
    old_archive = public / "processforge-1.2.0.zip"
    old_sidecar = public / "processforge-1.2.0.manifest.json"
    assert sha256(old_sidecar.read_bytes()) == PUBLIC_SIDECAR_SHA256
    old_metadata = verify_archive(
        old_archive, old_sidecar, PUBLIC_ZIP_SHA256, PUBLIC_COMMIT
    )
    target_metadata = verify_archive(archive, sidecar, args.sha256, args.commit)
    assert old_metadata["version"] == "1.2.0"
    root.mkdir(parents=True)
    out.mkdir(parents=True)
    report: dict[str, Any] = {
        "scope": "Core file replacement; project migration/worker acceptance is separate",
        "os": host_info.platform(),
        "kernel": host_info.release(),
        "python": sys.version,
        "old": old_metadata["source"],
        "candidate": target_metadata["source"],
        "old_archive_sha256": PUBLIC_ZIP_SHA256,
        "candidate_archive_sha256": args.sha256,
        "candidate_sidecar_sha256": sha256(sidecar.read_bytes()),
        "commands": [],
    }
    started = time.monotonic()
    temp = root / "t"
    temp.mkdir()
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("PF_", "PROCESSFORGE_")) and key != "PYTHONPATH"
    }
    environment.update(
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        PYTHONDONTWRITEBYTECODE="1",
        TEMP=str(temp),
        TMP=str(temp),
        TMPDIR=str(temp),
        LOCALAPPDATA=str(root / "config"),
        XDG_CONFIG_HOME=str(root / "config"),
    )

    def save(name: str, value: Any) -> None:
        (out / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def run(
        label: str, entry: Path, *arguments: str | Path, expected: int | None = 0
    ) -> tuple[int, dict[str, Any]]:
        command = [sys.executable, "-B", str(entry), *map(str, arguments)]
        remaining = 600 - (time.monotonic() - started)
        assert remaining > 0, "whole-flow deadline"
        tick = time.monotonic()
        budget = 180 if label == "07-apply" else 90
        try:
            process = subprocess.run(
                command,
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=min(budget, remaining),
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            for stream in ("stdout", "stderr"):
                partial = getattr(error, stream) or b""
                if isinstance(partial, bytes):
                    partial = partial.decode("utf-8", "replace")
                (out / (label + "." + stream + ".txt")).write_text(
                    partial, encoding="utf-8"
                )
            report["commands"].append(
                {
                    "id": label,
                    "argv": command,
                    "exit_code": "timeout",
                    "budget": min(budget, remaining),
                    "seconds": round(time.monotonic() - tick, 3),
                }
            )
            save("results.json", report)
            raise
        (out / (label + ".stdout.txt")).write_text(process.stdout, encoding="utf-8")
        (out / (label + ".stderr.txt")).write_text(process.stderr, encoding="utf-8")
        report["commands"].append(
            {
                "id": label,
                "argv": command,
                "exit_code": process.returncode,
                "budget": min(budget, remaining),
                "seconds": round(time.monotonic() - tick, 3),
            }
        )
        save("results.json", report)
        if expected is not None:
            assert process.returncode == expected, label
        try:
            result = json.loads(process.stdout)
        except json.JSONDecodeError:
            result = {}
        return process.returncode, result

    core, manager = root / "old-core", root / "manager"
    with zipfile.ZipFile(old_archive) as bundle:
        bundle.extractall(core)
        old_manifest = bundle.read("processforge-core.manifest.json")
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(manager)
        target_manifest = bundle.read("processforge-core.manifest.json")
    old_files = {row["relative_path"]: row for row in json.loads(old_manifest)["files"]}
    new_files = {
        row["relative_path"]: row for row in json.loads(target_manifest)["files"]
    }
    assert old_files["LICENSE"]["sha256"] == new_files["LICENSE"]["sha256"]
    assert old_files["NOTICE"]["sha256"] == new_files["NOTICE"]["sha256"]
    old_cli, cli = core / "bin/pf.py", manager / "bin/pf.py"
    workplace, project = root / "workplace", root / "project"
    run("01-old-version", old_cli, "version")
    run(
        "02-old-workplace",
        old_cli,
        "workplace-init",
        "--workplace",
        workplace,
        "--profile",
        "software-development",
        "--apply",
    )
    project.mkdir()
    (project / "README.md").write_text(
        "# Retained public release project\n", encoding="utf-8"
    )
    run(
        "03-old-project",
        old_cli,
        "project-init",
        "--project-root",
        project,
        "--workplace",
        workplace,
        "--type",
        "processforge-development",
        "--process",
        "software-feature-development",
        "--apply",
    )
    scope = {
        "schema_version": 1,
        "assignment": {
            "execution_mode": {
                "kind": "docs_only",
                "code_changes_allowed": False,
                "artifact_changes_allowed": True,
                "requires_review": True,
            },
            "allowed_actions": ["read", "write_artifact"],
            "allowed_files": [".pf/artifacts/retained/**"],
            "allowed_read_files": [
                "README.md",
                ".pf/process-forge.yaml",
                ".pf/assignments/**",
                ".pf/contexts/**",
            ],
            "required_sources": ["README.md"],
            "ownership": {
                "owner_id": "release-fixture",
                "role": "executor",
                "writer": True,
            },
        },
    }
    scope_path = root / "scope.json"
    scope_path.write_text(json.dumps(scope), encoding="utf-8")
    _, work = run(
        "04-old-work",
        old_cli,
        "work-start",
        "--project-root",
        project,
        "--workplace",
        workplace,
        "--objective",
        "Retained release qualification",
        "--process-id",
        "software-feature-development",
        "--scope-file",
        scope_path,
        "--json",
    )
    assert work["action"] == "created_new"
    (core / "LICENSE").write_bytes(b"local Core edit\n")
    (core / "NOTICE").unlink()
    sentinels = {
        "unknown-user.txt": b"unknown bytes\x00",
        ".pf/user-history.json": b'{"history":["keep"]}',
        "config/user.yaml": b"custom: true\n",
    }
    for name, content in sentinels.items():
        path = core / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    before = snapshot(core)
    project_before, workplace_before = snapshot(project), snapshot(workplace)
    save(
        "user-data-before.json",
        {"project": project_before, "workplace": workplace_before},
    )
    update = ("--core-root", core, "--archive", archive, "--workplace-root", workplace)
    _, plan = run("05-plan", cli, "core-update", "plan", *update)
    assert plan["status"] == "planned" and not plan["blockers"]
    assert "LICENSE" in plan["locally_modified"] and "NOTICE" in plan["missing_owned"]
    assert snapshot(core) == before
    _, refusal = run("06-no-confirm", cli, "core-update", "apply", *update, expected=1)
    assert refusal["error"]["code"] == "confirm_required" and snapshot(core) == before
    _, applied = run("07-apply", cli, "core-update", "apply", *update, "--confirm")
    assert applied["status"] == "applied" and applied["maintenance_mode"] == "file_only"
    for name, row in new_files.items():
        assert sha256((core / name).read_bytes()) == row["sha256"], name
    assert (core / "processforge-core.manifest.json").read_bytes() == target_manifest
    assert all(
        not (core / name).exists() for name in old_files.keys() - new_files.keys()
    )
    assert all(
        (core / name).read_bytes() == content for name, content in sentinels.items()
    )
    backup = Path(applied["backup_dir"])
    assert (backup / "files/LICENSE").read_bytes() == b"local Core edit\n"
    assert applied["backed_up"]["NOTICE"] is None
    assert (backup / "control/old-manifest.json").read_bytes() == old_manifest
    for name in (".pf/AGENTS.md", ".pf/hooks.yaml", ".pf/process-forge.yaml"):
        assert (
            sha256((backup / applied["backed_up"][name]).read_bytes())
            == old_files[name]["sha256"]
        )
    assert (
        snapshot(project) == project_before and snapshot(workplace) == workplace_before
    )
    report["user_data_byte_parity"] = True
    _, status = run("08-status", cli, "core-update", "status", "--core-root", core)
    assert (
        status["version"] == target_metadata["version"]
        and not status["incomplete_update"]
    )
    run("09-upgraded-version", old_cli, "version")
    _, retained = run(
        "10-retained-work",
        old_cli,
        "work-state",
        "--project-root",
        project,
        "--run",
        work["run_id"],
        "--assignment",
        work["assignment_id"],
        "--context-id",
        work["context"]["id"],
        "--json",
    )
    assert retained["assignment"]["id"] == work["assignment_id"]
    assert retained["context"]["checksum"] == work["context"]["checksum"]
    report["core_file_checks"] = "passed"
    run("11-workplace-doctor", old_cli, "doctor-workplace", "--root", workplace)
    migration_code, migration = run(
        "12-storage-migration",
        core / "tools/migrate-storage.py",
        "--project-root",
        project,
        "--workplace-root",
        workplace,
        "--apply",
        "--json",
        expected=None,
    )
    prepare_code, _ = run(
        "13-worker-prepare",
        old_cli,
        "worker-run",
        "prepare",
        "--project-root",
        project,
        "--task",
        work["assignment_id"],
        "--driver",
        "codex-exec",
        expected=None,
    )
    report["project_migration"] = {"exit_code": migration_code, "result": migration}
    report["worker_prepare_exit_code"] = prepare_code
    report["full_t06_qualified"] = False
    report["limit"] = (
        "No native adoption, SQL cutover or worker start/status/collect is inferred."
    )
    report["seconds"] = round(time.monotonic() - started, 3)
    save("results.json", report)
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "core_file_checks",
                    "user_data_byte_parity",
                    "full_t06_qualified",
                    "candidate_archive_sha256",
                    "seconds",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
