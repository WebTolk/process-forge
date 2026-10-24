"""Public DTO validation and import/construction side-effect checks."""

import os
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from processforge_core.database import (
    Database,
    DatabaseError,
    DatabaseFactory,
    DatabaseIdentity,
    DatabaseTarget,
    SQLiteDriver,
    SqlRow,
    SqlStatement,
)

from . import isolated_path

tmp_path = isolated_path


@pytest.mark.parametrize(
    "value", [True, False, 2**63, -(2**63) - 1, float("inf"), float("nan"), object()]
)
def test_invalid_values(value):
    with pytest.raises(DatabaseError, match="^database_constraint_failed$"):
        SqlStatement("SELECT ?", (value,))


def test_row_and_statement():
    row = SqlRow(("a", "b"), (1, b"x"))
    assert row[0] == row["a"] == 1
    assert row[-1] == b"x"
    with pytest.raises(KeyError):
        row["missing"]
    with pytest.raises(FrozenInstanceError):
        row.columns = ("c",)
    with pytest.raises(DatabaseError):
        SqlRow(("a", "a"), (1, 2))
    with pytest.raises(DatabaseError, match="database_dialect_unsupported"):
        SqlStatement("SELECT 1", dialect="other")


def test_cold_import_and_factory(tmp_path):
    code = """
import sqlite3
from pathlib import Path
def denied(*args, **kwargs):
    raise AssertionError("cold I/O")
sqlite3.connect = denied
Path.mkdir = denied
Path.exists = denied
Path.resolve = denied
from processforge_core.database import DatabaseFactory, DatabaseIdentity, DatabaseTarget
database = DatabaseFactory.from_profile(None, "project_main", DatabaseTarget(Path.cwd() / "missing" / "pf.sqlite3", DatabaseIdentity("a" * 32, "project", "owner")))
assert database.timeout_ms == 100
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert list(tmp_path.iterdir()) == []


def test_wildcard_only_for_inspection(tmp_path):
    target = DatabaseTarget(
        tmp_path / "missing.sqlite3", DatabaseIdentity(None, "project", "p")
    )
    database = Database(SQLiteDriver(), target)
    for operation in (database.read, database.transaction):
        with pytest.raises(DatabaseError, match="database_foreign"):
            operation()
    with pytest.raises(DatabaseError):
        DatabaseFactory.from_profile(None, "project_main", target)
    assert not target.path.exists()


def test_invalid_target_and_identity():
    for store in ("", "bad", "a" * 31):
        with pytest.raises(DatabaseError):
            DatabaseIdentity(store, "project", "p")
    with pytest.raises(DatabaseError):
        DatabaseTarget(
            Path("relative.sqlite3"), DatabaseIdentity("a" * 32, "project", "p")
        )
