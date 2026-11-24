"""Run the contract probes against one explicitly selected distribution."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

import pytest

HARNESS_ROOT = Path(__file__).resolve().parents[2]
PUBLISHED_ARCHIVE_SHA256 = (
    "80a4f15b1f4cfdce66dec44d15fbc9a9cc1fd615d8dc4c9c75ab872be679684a"
)
PUBLISHED_COMMIT = "804c53a775b963aceddc5759f8d94a8ed4b8d533"
PUBLISHED_TREE = "10e41b987223c6c5ec98b723eeb473e5e0e7df5d"
POST_FIX_COMMIT = "336b61d470c2a68b4091e6667921a22ecf135ce5"
POST_FIX_TREE = "db45ebc46e34f3c4ef4da6ae376657ff0561f2b8"


@dataclass(frozen=True)
class ContractDistribution:
    """Supply one target root and isolated subprocess inputs to the probes."""

    root: Path
    profile: str

    @property
    def environment(self) -> dict[str, str]:
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.upper().startswith(("PF_", "PROCESSFORGE_", "PYTHON", "GIT_"))
        }
        env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
        return env

    def run(
        self,
        *args: str | Path,
        entry: str = "bin/pf.py",
        input_text: str | None = None,
        timeout: float = 120.0,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(self.root / entry), *map(str, args)],
            cwd=self.root,
            env=self.environment,
            input=input_text,
            capture_output=True,
            encoding="utf-8",
            timeout=timeout,
            check=False,
        )


def _git(root: Path, environment: dict[str, str], *args: str) -> str:
    return subprocess.run(
        ["git", "--no-optional-locks", "-C", str(root), *args],
        env=environment,
        capture_output=True,
        encoding="utf-8",
        timeout=60,
        check=True,
    ).stdout.strip()


def _verify_published(root: Path, archive: Path) -> None:
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    assert digest == PUBLISHED_ARCHIVE_SHA256, (archive, digest)
    with ZipFile(archive) as distribution:
        manifest = json.loads(distribution.read("processforge-core.manifest.json"))
        assert manifest["source"]["commit"] == PUBLISHED_COMMIT
        assert manifest["source"]["tree"] == PUBLISHED_TREE
        entries = [entry for entry in distribution.infolist() if not entry.is_dir()]
        expected = {entry.filename for entry in entries}
        actual = {
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file()
        }
        assert actual == expected, (
            "Published distribution inventory differs",
            sorted(expected - actual),
            sorted(actual - expected),
        )
        for entry in entries:
            installed = root / entry.filename
            assert not installed.is_symlink(), entry.filename
            assert installed.read_bytes() == distribution.read(entry), entry.filename


@pytest.fixture(scope="session")
def contract_distribution() -> ContractDistribution:
    profile = os.environ.get("PF_CONTRACT_PROFILE", "candidate")
    root_value = os.environ.get("PF_CONTRACT_ROOT")
    if profile != "candidate" and not root_value:
        raise pytest.UsageError(f"PF_CONTRACT_ROOT is required for {profile}")
    root = Path(root_value).resolve() if root_value else HARNESS_ROOT
    assert (root / "bin" / "pf.py").is_file(), f"No ProcessForge CLI at {root}"
    assert (root / "tools" / "pf_runtime" / "mcp_server.py").is_file(), root
    distribution = ContractDistribution(root, profile)
    environment = distribution.environment

    match profile:
        case "published-1.3.0":
            archive_value = os.environ.get("PF_CONTRACT_ARCHIVE")
            if not archive_value:
                raise pytest.UsageError(
                    "PF_CONTRACT_ARCHIVE must name the official 1.3.0 ZIP"
                )
            _verify_published(root, Path(archive_value))
            commit, tree = PUBLISHED_COMMIT, PUBLISHED_TREE
        case "post-119-120" | "candidate":
            expected_commit = (
                POST_FIX_COMMIT
                if profile == "post-119-120"
                else os.environ.get("PF_CONTRACT_EXPECTED_COMMIT")
            )
            commit, tree = _git(
                root, environment, "rev-parse", "HEAD", "HEAD^{tree}"
            ).splitlines()
            if expected_commit:
                assert commit == expected_commit, (expected_commit, commit)
                assert not _git(root, environment, "status", "--porcelain"), root
            if profile == "post-119-120":
                assert tree == POST_FIX_TREE, tree
        case _:
            raise pytest.UsageError(f"Unrecognized PF_CONTRACT_PROFILE: {profile}")

    harness_commit = _git(HARNESS_ROOT, environment, "rev-parse", "HEAD")
    harness_dirty = bool(_git(HARNESS_ROOT, environment, "status", "--porcelain"))
    fixture_digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    verified = profile != "candidate" or bool(
        os.environ.get("PF_CONTRACT_EXPECTED_COMMIT")
    )
    print(
        f"ProcessForge contract target profile={profile} root={root} "
        f"commit={commit} tree={tree} verified={verified} "
        f"harness_commit={harness_commit} harness_dirty={harness_dirty} fixture_sha256={fixture_digest}"
    )
    return distribution
