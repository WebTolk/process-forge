"""Check native journal persistence and the independent public archive flow."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from uuid import UUID, uuid4
from zipfile import ZipFile

import pytest
from conftest import ContractDistribution, verify_published_archive

ARCHIVE_SHA256 = "80a4f15b1f4cfdce66dec44d15fbc9a9cc1fd615d8dc4c9c75ab872be679684a"
MANIFEST_SHA256 = "7c338d0546c3c081cf7b568a79922caa8ef4cc0f76f4b2cdd3039a1b21442518"
PROCESS = "task-batch-execution"
RUN_CREATED = "run.created"
ARCHIVE_EVIDENCE = Path(".pf/runtime/release-test/commands")


def test_project_journal_uuid(
    contract_distribution: ContractDistribution, tmp_path: Path
) -> None:
    project = tmp_path / "p"
    workplace = tmp_path / "w"
    project.mkdir()

    run = contract_distribution.run
    initialized_workplace = run("workplace-init", "--workplace", workplace, "--apply")
    assert initialized_workplace.returncode == 0, initialized_workplace
    project_args = ("--project-root", project, "--workplace", workplace)
    initialized_project = run(
        "project-init",
        *project_args,
        "--type",
        "generic",
        "--coordination-mode",
        "simple",
        "--process",
        PROCESS,
        "--apply",
    )
    assert initialized_project.returncode == 0, initialized_project
    assert not initialized_project.stderr, initialized_project

    journal = project / ".pf/runtime/events/events.sqlite3"
    uri = journal.as_uri() + "?mode=ro"
    store_id_sql = "SELECT store_id FROM pf_store_meta"
    event_sql = "SELECT event_id, event_type, subject FROM events WHERE event_type=? AND subject=?"
    run_id = "storage-" + uuid4().hex
    with closing(sqlite3.connect(uri, uri=True)) as db:
        [(store_id,)] = db.execute(store_id_sql).fetchall()
        assert UUID(store_id).int
        assert not db.execute(event_sql, (RUN_CREATED, run_id)).fetchall()

    created = run(
        "run-create",
        "--project-root",
        project,
        "--id",
        run_id,
        "--title",
        "Journal persistence probe",
        "--process",
        PROCESS,
        "--apply",
    )
    assert created.returncode == 0 and not created.stderr, created
    assert f"WROTE: .pf/runs/{run_id}/run.yaml" in created.stdout
    with closing(sqlite3.connect(uri, uri=True)) as db:
        [(event_id, event_type, subject)] = db.execute(
            event_sql, (RUN_CREATED, run_id)
        ).fetchall()
    assert isinstance(event_id, str) and event_id
    assert (event_type, subject) == (RUN_CREATED, run_id)

    status = run("project-init-status", *project_args, "--json")
    assert status.returncode == 0 and not status.stderr, status
    payload = json.loads(status.stdout)
    assert payload["kind"] == "pf.project_initialization.status", payload
    assert payload["workplace"] == "reachable", payload
    assert payload["missing_deterministic_artifacts"] == [], payload
    assert payload["agent_entry"]["status"] == "current", payload
    assert payload["state"] == payload["snapshot_health"] == "blocked", payload
    with closing(sqlite3.connect(uri, uri=True)) as db:
        assert db.execute(store_id_sql).fetchall() == [(store_id,)]
        assert db.execute(event_sql, (RUN_CREATED, run_id)).fetchall() == [
            (event_id, event_type, subject)
        ]
    print(
        f"journal: state={payload['state']} store_id={store_id} "
        f"event_id={event_id} subject={subject}"
    )


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _assets() -> tuple[Path, Path]:
    archive_value = os.environ.get("PF_CONTRACT_ARCHIVE")
    if not archive_value:
        reason = "Set PF_CONTRACT_ARCHIVE to the official 1.3.0 ZIP"
        if os.environ.get("PF_CONTRACT_PROFILE") or os.environ.get(
            "PF_CONTRACT_EXPECTED_COMMIT"
        ):
            raise pytest.UsageError(reason)
        pytest.skip(reason)
    archive = Path(archive_value).resolve()
    manifest = archive.with_suffix(".manifest.json")
    _verify_assets(archive, manifest)
    return archive, manifest


def _verify_assets(archive: Path, manifest: Path) -> None:
    assert _sha256(archive) == ARCHIVE_SHA256
    assert _sha256(manifest) == MANIFEST_SHA256


def _published_inventory(root: Path) -> set[Path]:
    return {path.relative_to(root) for path in root.rglob("*") if path.is_file()}


def _copy_driver(
    distribution: ContractDistribution, destination: Path
) -> dict[Path, str]:
    root = distribution.root
    if distribution.profile == "published-1.3.0":
        files = _published_inventory(root)
    else:
        listed = subprocess.run(
            ["git", "--no-optional-locks", "ls-files", "-z"],
            cwd=root,
            env=distribution.environment,
            capture_output=True,
            encoding="utf-8",
            check=True,
            timeout=60,
        )
        files = {Path(name) for name in listed.stdout.split("\0") if name}
    digests = {}
    for name in sorted(files):
        source = root / name
        assert not source.is_symlink(), name
        dest = destination / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        digests[name] = _sha256(source)
        assert _sha256(dest) == digests[name], name
    assert files and not (destination / ARCHIVE_EVIDENCE).exists()
    return digests


def _run_archive(
    distribution: ContractDistribution,
    driver: Path,
    archive: Path,
    manifest: Path,
    extraction: Path,
    *,
    extracted_test: str,
) -> subprocess.CompletedProcess[str]:
    extraction.mkdir()
    env = distribution.environment
    env.update(TMPDIR=str(extraction), TMP=str(extraction), TEMP=str(extraction))
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(driver / "bin/pf.py"),
            "release-archive-test",
            "--archive",
            str(archive),
            "--manifest",
            str(manifest),
            "--extracted-test",
            extracted_test,
        ],
        cwd=driver,
        env=env,
        capture_output=True,
        encoding="utf-8",
        check=False,
        timeout=1260,
    )


def _verify_driver_reference(
    distribution: ContractDistribution, digests: dict[Path, str]
) -> None:
    if distribution.profile == "published-1.3.0":
        assert _published_inventory(distribution.root) == digests.keys()
    for name, expected in digests.items():
        assert _sha256(distribution.root / name) == expected, name


def _save_result(
    destination: Path, name: str, result: subprocess.CompletedProcess[str]
) -> None:
    (destination / f"{name}-stdout.log").write_text(result.stdout, encoding="utf-8")
    (destination / f"{name}-stderr.log").write_text(result.stderr, encoding="utf-8")
    (destination / f"{name}-result.json").write_text(
        json.dumps({"args": result.args, "returncode": result.returncode}) + "\n",
        encoding="utf-8",
    )


def test_release_archive_validation_and_extracted_cli(
    contract_distribution: ContractDistribution, tmp_path: Path
) -> None:
    archive, manifest = _assets()
    driver = tmp_path / "driver"
    digests = _copy_driver(contract_distribution, driver)
    inspected = _run_archive(
        contract_distribution,
        driver,
        archive,
        manifest,
        tmp_path / "t",
        extracted_test="skip",
    )
    _save_result(tmp_path, "manifest", inspected)
    assert inspected.returncode == 0 and not inspected.stderr, inspected
    assert "PASS: release manifest archive sha256 matches zip bytes" in inspected.stdout
    assert inspected.stdout.splitlines()[-1] == "RESULT: PASS", inspected
    assert not (driver / ARCHIVE_EVIDENCE).exists()

    extracted = tmp_path / "extracted"
    with ZipFile(archive) as distribution:
        distribution.extractall(extracted)
    verify_published_archive(extracted, archive)
    checks = ("schema validation", "public cleanliness", "checksum")
    tested = ContractDistribution(extracted, "published-1.3.0").run(
        "release-test",
        "--root",
        extracted,
        *(arg for check in checks for arg in ("--only", check)),
        timeout=360,
    )
    _save_result(tmp_path, "extracted", tested)
    _verify_assets(archive, manifest)
    _verify_driver_reference(contract_distribution, digests)
    assert tested.returncode == 0 and not tested.stderr, tested
    lines = tested.stdout.splitlines()
    for check in checks:
        assert f"PASS {check}" in lines, tested
    assert [line for line in lines if line.startswith("WARN ")] == [
        "WARN git diff --check skipped: not a git repo"
    ], tested
    assert lines[-1] == "RESULT: PASS with warnings", tested
    print(f"archive: manifest and extracted CLI passed sha256={ARCHIVE_SHA256}")


def test_release_archive_refuses_mismatched_manifest(
    contract_distribution: ContractDistribution, tmp_path: Path
) -> None:
    archive, manifest = _assets()
    driver = tmp_path / "driver"
    digests = _copy_driver(contract_distribution, driver)
    mismatched = tmp_path / "mismatched.manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["archive"]["sha256"] = "0" * 64
    mismatched.write_text(json.dumps(data), encoding="utf-8")
    extraction = tmp_path / "t"

    result = _run_archive(
        contract_distribution,
        driver,
        archive,
        mismatched,
        extraction,
        extracted_test="quick",
    )

    _verify_assets(archive, manifest)
    _verify_driver_reference(contract_distribution, digests)
    assert result.returncode == 1 and not result.stderr, result
    assert "FAIL: release manifest archive sha256 matches zip bytes" in result.stdout, (
        result
    )
    assert not any(
        line.startswith(("RUN ", "EVIDENCE: ")) for line in result.stdout.splitlines()
    ), result
    assert not any(extraction.iterdir())
    assert not (driver / ARCHIVE_EVIDENCE).exists()
    print(
        f"archive: mismatched manifest exit={result.returncode} sha256={ARCHIVE_SHA256}"
    )
