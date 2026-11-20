"""Index readers refuse races and lock contention without creating a database."""

from __future__ import annotations

import hashlib
import importlib
import sqlite3
import time
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


@pytest.fixture
def index_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "src"))
    return importlib.import_module("processforge_core.resources.local_search")


def _seed(module: ModuleType, root: Path) -> tuple[Path, dict[str, Any]]:
    documents = root / "documents"
    documents.mkdir(parents=True)
    (documents / "guide.md").write_text("readonly-invariant-marker", encoding="utf-8")
    snapshot = {
        "snapshot": {"id": "fixture", "checksum": "fixture-sha"},
        "local_search_resources": [
            {
                "id": "fixture:docs",
                "content_roots": [str(documents)],
                "indexing": {"mode": "fulltext"},
            }
        ],
    }
    result = module.build_index(root, snapshot, workplace_root=root)
    assert result["status"] == "fresh"
    return module.index_path(root, root), snapshot


def test_disappearing_index_is_never_recreated(
    index_module: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database, snapshot = _seed(index_module, tmp_path)
    original = Path.is_file
    removed = False

    def disappear(path: Path) -> bool:
        nonlocal removed
        exists = original(path)
        if path == database and exists and not removed:
            removed = True
            database.unlink()
        return exists

    monkeypatch.setattr(Path, "is_file", disappear)
    result = index_module.index_status(tmp_path, snapshot, workplace_root=tmp_path)
    assert removed
    assert not database.exists()
    assert result["status"] != "fresh"


@pytest.mark.parametrize("operation", ["status", "coverage", "search"])
def test_busy_reader_returns_without_default_wait(
    index_module: ModuleType, tmp_path: Path, operation: str
) -> None:
    database, snapshot = _seed(index_module, tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute("BEGIN EXCLUSIVE")
        started = time.monotonic()
        if operation == "status":
            result = index_module.index_status(
                tmp_path, snapshot, workplace_root=tmp_path
            )
            assert result["status"] != "fresh"
        elif operation == "coverage":
            result = index_module.authorized_coverage(
                tmp_path, snapshot, workplace_root=tmp_path
            )
            assert result["status"] != "complete"
        else:
            result = index_module.search(
                tmp_path,
                snapshot,
                query="readonly-invariant-marker",
                workplace_root=tmp_path,
            )
            assert result["search_status"] != "fresh"
            assert result["results"] == []
        elapsed = time.monotonic() - started
        # Generous bound distinguishes a nonwaiting refusal from SQLite's 5 s
        # default busy timeout without depending on submillisecond timing.
        assert elapsed < 1.5, elapsed
    finally:
        connection.rollback()
        connection.close()


@pytest.mark.parametrize("name", ["plain", "данные # percent %"])
def test_normal_readers_preserve_database_bytes_and_results(
    index_module: ModuleType, tmp_path: Path, name: str
) -> None:
    root = tmp_path / name
    database, snapshot = _seed(index_module, root)
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    status = index_module.index_status(root, snapshot, workplace_root=root)
    coverage = index_module.authorized_coverage(root, snapshot, workplace_root=root)
    result = index_module.search(
        root, snapshot, query="readonly-invariant-marker", workplace_root=root
    )
    assert status["status"] == "fresh"
    assert coverage["status"] == "complete"
    assert result["search_status"] == "fresh"
    assert result["results"][0]["resource_id"] == "fixture:docs"
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before


def test_missing_index_has_no_filesystem_side_effects(
    index_module: ModuleType, tmp_path: Path
) -> None:
    snapshot = {"local_search_resources": []}
    before = set(tmp_path.rglob("*"))
    assert (
        index_module.index_status(tmp_path, snapshot, workplace_root=tmp_path)["status"]
        == "missing"
    )
    assert (
        index_module.search(
            tmp_path, snapshot, query="anything", workplace_root=tmp_path
        )["results"]
        == []
    )
    index_module.authorized_coverage(tmp_path, snapshot, workplace_root=tmp_path)
    assert set(tmp_path.rglob("*")) == before


def test_readers_observe_committed_wal_contents(
    index_module: ModuleType, tmp_path: Path
) -> None:
    database, snapshot = _seed(index_module, tmp_path)
    writer = sqlite3.connect(database)
    try:
        assert writer.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        writer.execute("UPDATE documents SET title=title")
        writer.commit()
        assert (
            index_module.index_status(tmp_path, snapshot, workplace_root=tmp_path)[
                "status"
            ]
            == "fresh"
        )
        result = index_module.search(
            tmp_path,
            snapshot,
            query="readonly-invariant-marker",
            workplace_root=tmp_path,
        )
        assert result["results"][0]["resource_id"] == "fixture:docs"
    finally:
        writer.close()
