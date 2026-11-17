#!/usr/bin/env python3
"""Qualify public Core replacement, explicit migration and retained Work/worker."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform as host_info
import sqlite3
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


def file_recovery(args: argparse.Namespace) -> int:
    """Qualify public CLI recovery after an actual native filesystem failure."""
    import ctypes

    root, out = args.root.resolve(), args.out.resolve()
    assert not root.exists() and not out.exists()
    old_archive = args.public_dir / "processforge-1.2.0.zip"
    old_sidecar = args.public_dir / "processforge-1.2.0.manifest.json"
    assert sha256(old_sidecar.read_bytes()) == PUBLIC_SIDECAR_SHA256
    verify_archive(old_archive, old_sidecar, PUBLIC_ZIP_SHA256, PUBLIC_COMMIT)
    metadata = verify_archive(args.candidate, args.sidecar, args.sha256, args.commit)
    root.mkdir(parents=True)
    out.mkdir(parents=True)
    manager, core, workplace, temp = (
        root / n for n in ("manager", "core", "workplace", "temp")
    )
    workplace.mkdir()
    temp.mkdir()
    (workplace / "workplace.yaml").write_bytes(
        b"schema_version: 1\nid: recovery-fixture\n"
    )
    with zipfile.ZipFile(old_archive) as bundle:
        bundle.extractall(core)
        old_manifest = bundle.read("processforge-core.manifest.json")
    with zipfile.ZipFile(args.candidate) as bundle:
        bundle.extractall(manager)
        new_manifest = bundle.read("processforge-core.manifest.json")
        payload = {
            r["relative_path"]: bundle.read(r["relative_path"])
            for r in json.loads(new_manifest)["files"]
        }
    sentinels = {
        "unknown.bin": b"unknown\x00bytes",
        ".pf/user-history.json": b"private history",
        "config/user.yaml": b"custom: true\n",
        "runtime/user/keep": b"user runtime",
    }
    (core / "LICENSE").write_bytes(b"local license preimage\n")
    (core / "NOTICE").unlink()
    for name, raw in sentinels.items():
        path = core / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    before = snapshot(core)
    report: dict[str, Any] = {
        "os": host_info.platform(),
        "python": sys.version,
        "source": metadata["source"],
        "archive_sha256": args.sha256,
        "old_manifest_sha256": sha256(old_manifest),
        "new_manifest_sha256": sha256(new_manifest),
        "commands": [],
        "matrix": {
            "actual_os_failure_before_manifest": "pending",
            "default_readonly": "pending",
            "no_confirm": "pending",
            "wrong_archive": "pending",
            "recovery_fails_again": "pending",
            "confirmed_recovery": "pending",
            "target_bytes_preimages_unknown": "pending",
        },
    }

    def save() -> None:
        (out / "receipt.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )

    save()  # Pins and scenario matrix precede execution.
    environment = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("PF_", "PROCESSFORGE_")) and k != "PYTHONPATH"
    }
    environment.update(
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        TEMP=str(temp),
        TMP=str(temp),
        TMPDIR=str(temp),
        LOCALAPPDATA=str(root / "config"),
        XDG_CONFIG_HOME=str(root / "config"),
    )

    def run(
        label: str, command: str, options: list[str], expected: int
    ) -> dict[str, Any]:
        argv = [
            sys.executable,
            "-I",
            "-B",
            str(manager / "bin/pf.py"),
            "core-update",
            command,
            "--core-root",
            str(core),
            *options,
        ]
        tick = time.monotonic()
        result = subprocess.run(
            argv,
            cwd=root,
            env=environment,
            capture_output=True,
            timeout=180,
            check=False,
        )
        for stream in ("stdout", "stderr"):
            (out / (label + "." + stream + ".txt")).write_bytes(getattr(result, stream))
        report["commands"].append(
            {
                "id": label,
                "argv": argv,
                "exit": result.returncode,
                "seconds": round(time.monotonic() - tick, 3),
            }
        )
        save()
        assert result.returncode == expected, (label, result.stdout, result.stderr)
        return json.loads(result.stdout)

    update = [
        "--archive",
        str(args.candidate.resolve()),
        "--workplace-root",
        str(workplace),
    ]
    plan = run("01-plan", "plan", update, 0)
    assert plan["status"] == "planned"
    report["counts"] = plan["counts"]
    # Windows denies replacement of VERSION through an actual OS share lock.
    # Linux denies creation/replacement in one changed payload parent as a normal user.
    handle = None
    denied = core / "tools"
    mode = denied.stat().st_mode
    if os.name == "nt":
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        handle = kernel.CreateFileW(
            str(core / "VERSION"), 0x80000000, 1, None, 3, 0, None
        )
        assert handle != wintypes.HANDLE(-1).value
        report["fault"] = "CreateFileW read sharing only"
    else:
        assert getattr(os, "geteuid")() != 0, (
            "Linux denial qualification requires a normal user"
        )
        # This directory is new in public 1.2.0, so deny its existing parent.
        denied = core / "tools"
        mode = denied.stat().st_mode
        denied.chmod(0o555)
        report["fault"] = "chmod 0555 on tools parent"
    try:
        failed = run("02-locked-apply", "apply", [*update, "--confirm"], 1)
        assert failed["error"]["code"] == "file_operation_failed"
        journal_path = core / "runtime/core-update/in-progress.json"
        journal_raw = journal_path.read_bytes()
        progress = json.loads(journal_raw)
        assert (
            progress["status"] == "failed"
            and progress["recovery_evidence"]["version"] == 1
        )
        assert (
            progress["error"]["winerror"] in {5, 32}
            if os.name == "nt"
            else progress["error"]["errno"] == 13
        )
        assert (core / "processforge-core.manifest.json").read_bytes() == old_manifest
        assert all(
            op["op"] != "write_manifest" for op in progress["completed_operations"]
        )
        (out / "failed-journal.json").write_bytes(journal_raw)
        backup = Path(progress["backup_dir"])
        retained = {
            p.relative_to(backup).as_posix(): p.read_bytes()
            for p in backup.rglob("*")
            if p.is_file()
        }
        proof = json.loads((backup / "control/recovery-proof.json").read_bytes())
        assert proof["archive"]["sha256"] == args.sha256
        for name, initial in proof["initial"].items():
            assert initial == (
                {
                    "sha256": before[name],
                    "size": (backup / "files" / name).stat().st_size,
                }
                if name in before
                else None
            )
            if initial is not None:
                assert (
                    sha256((backup / "files" / name).read_bytes()) == initial["sha256"]
                )
        assert set(progress["backed_up"]) == set(plan["removed"]) | set(
            plan["changed"]
        ) | set(plan["restored"])
        report["matrix"]["actual_os_failure_before_manifest"] = "pass"
        stable = snapshot(core)
        status = run("03-readonly-repair", "repair", [], 0)
        assert status["status"] == "safe_to_rollback" and snapshot(core) == stable
        report["matrix"]["default_readonly"] = "pass"
        no_confirm = run("04-no-confirm", "repair", ["--resume", *update], 1)
        assert (
            no_confirm["error"]["code"] == "confirm_required"
            and snapshot(core) == stable
        )
        report["matrix"]["no_confirm"] = "pass"
        wrong = root / "wrong.zip"
        wrong.write_bytes(b"wrong archive")
        wrong_result = run(
            "05-wrong-archive",
            "repair",
            [
                "--resume",
                "--archive",
                str(wrong),
                "--workplace-root",
                str(workplace),
                "--confirm",
            ],
            1,
        )
        assert (
            wrong_result["error"]["code"] == "plan_blocked" and snapshot(core) == stable
        )
        report["matrix"]["wrong_archive"] = "pass"
        again = run("06-locked-resume", "repair", ["--resume", *update, "--confirm"], 1)
        assert again["error"]["code"] == "file_operation_failed"
        second = json.loads(journal_path.read_bytes())
        assert len(second["failure_history"]) == 2
        assert second["failure_history"][0] == progress["failure_history"][0]
        report["matrix"]["recovery_fails_again"] = "pass"
    finally:
        if os.name == "nt":
            assert kernel.CloseHandle(handle)
        else:
            denied.chmod(mode)
        save()
    recovered = run(
        "07-confirmed-resume", "repair", ["--resume", *update, "--confirm"], 0
    )
    assert recovered["status"] == "applied" and recovered["resumed"]
    assert recovered["update_id"] == progress["update_id"]
    assert recovered["failure_history"] == second["failure_history"]
    assert not journal_path.exists()
    assert all((backup / name).read_bytes() == raw for name, raw in retained.items())
    assert any(
        p.read_bytes() == journal_raw
        for p in (backup / "control").glob("resume-*.json")
    )
    assert all((core / name).read_bytes() == raw for name, raw in payload.items())
    assert (core / "processforge-core.manifest.json").read_bytes() == new_manifest
    assert all(not (core / name).exists() for name in plan["removed"])
    assert all((core / name).read_bytes() == raw for name, raw in sentinels.items())
    status = run("08-final-status", "status", [], 0)
    assert not status["incomplete_update"]
    report["verified_target_files"] = len(payload)
    report["verified_initial_entries"] = len(proof["initial"])
    report["matrix"]["confirmed_recovery"] = "pass"
    report["matrix"]["target_bytes_preimages_unknown"] = "pass"
    report["full_t06_accepted"] = False
    save()
    print(json.dumps(report["matrix"], indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(__doc__)
    for name in ("public-dir", "candidate", "sidecar", "root", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument(
        "--file-recovery",
        action="store_true",
        help="Run bounded real OS-failure and public CLI recovery qualification only.",
    )
    args = parser.parse_args()
    if args.file_recovery:
        return file_recovery(args)
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
        "scope": "Public Core update, explicit journal migration and retained Work/worker",
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
            "expected_report": {
                "artifact": ".pf/artifacts/retained/report.md",
                "format": "markdown",
            },
            "allowed_read_files": [
                ".pf/**",
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
    _, applied = run(
        "07-apply",
        cli,
        "core-update",
        "apply",
        *update,
        "--confirm",
    )
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
    worker = ("--project-root", project, "--task", work["assignment_id"])
    blocked_code, _ = run(
        "12-legacy-write-blocked",
        old_cli,
        "worker-run",
        "prepare",
        *worker,
        "--driver",
        "test-echo-worker",
        expected=1,
    )
    assert blocked_code == 1
    assert "storage_migration_required" in (
        out / "12-legacy-write-blocked.stdout.txt"
    ).read_text(encoding="utf-8")
    legacy_sources = {
        path: path.read_bytes()
        for base in (project, workplace)
        for path in base.rglob("*.ndjson")
    }
    _, journals = run(
        "13-journal-import",
        old_cli,
        "journal-maintenance",
        "import",
        "--project-root",
        project,
        "--workplace",
        workplace,
        "--apply",
    )
    assert journals["status"] == "ready", journals
    migration_args = (
        "--project-root",
        project,
        "--workplace-root",
        workplace,
        "--offline-confirmed",
        "--json",
    )
    _, migration = run(
        "14-storage-migration",
        core / "tools/migrate-storage.py",
        *migration_args,
        "--apply",
    )
    assert migration["status"] == "ready", migration
    identity_path = project / ".pf/data/execution-storage.json"
    identity_bytes = identity_path.read_bytes()
    _, repeated = run(
        "15-storage-resume",
        core / "tools/migrate-storage.py",
        *migration_args,
        "--resume",
    )
    assert (
        repeated["status"] == "ready" and identity_path.read_bytes() == identity_bytes
    )
    assert all(path.read_bytes() == raw for path, raw in legacy_sources.items())
    run(
        "16-worker-prepare",
        old_cli,
        "worker-run",
        "prepare",
        *worker,
        "--driver",
        "test-echo-worker",
    )
    run(
        "17-worker-start",
        old_cli,
        "worker-run",
        "start",
        *worker,
        "--driver",
        "test-echo-worker",
        "--wait",
    )
    run("18-worker-collect", old_cli, "worker-run", "collect", *worker)
    assert (project / ".pf/artifacts/retained/report.md").is_file()
    binding = json.loads(identity_bytes)
    database = project / ".pf" / binding["target_relative_path"]
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as sql:
        assert sql.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert sql.execute("SELECT COUNT(*) FROM execution_current").fetchone()[0] == 0
        attempt = sql.execute(
            "SELECT phase,outcome,collection FROM execution_attempts WHERE task_id=?",
            (work["assignment_id"],),
        ).fetchone()
        assert attempt == ("absent", "completed", "collected"), attempt
    report["project_migration"] = {"status": "ready", "source_bytes_preserved": True}
    report["retained_worker"] = {"status": "completed", "collection": "collected"}
    report["full_t06_qualified"] = True
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
