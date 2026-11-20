"""Cold, synchronous SQL contracts. Targets are authorized by host composition."""

from __future__ import annotations

import math
import re
from collections.abc import Iterator, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, TypeAlias

from .errors import DatabaseError

SqlValue: TypeAlias = None | int | float | str | bytes


def _values(values: tuple[SqlValue, ...]) -> None:
    if type(values) is not tuple:
        raise DatabaseError("database_constraint_failed")
    for value in values:
        if type(value) not in (type(None), int, float, str, bytes):
            raise DatabaseError("database_constraint_failed")
        if type(value) is int and not -(2**63) <= value < 2**63:
            raise DatabaseError("database_constraint_failed")
        if type(value) is float and not math.isfinite(value):
            raise DatabaseError("database_constraint_failed")


@dataclass(frozen=True)
class SqlStatement:
    """SQLite SQL with positional bound values; never interpolate values."""

    text: str
    params: tuple[SqlValue, ...] = ()
    dialect: Literal["sqlite"] = "sqlite"

    def __post_init__(self) -> None:
        if self.dialect != "sqlite":
            raise DatabaseError("database_dialect_unsupported")
        if type(self.text) is not str or not self.text.strip() or "\x00" in self.text:
            raise DatabaseError("database_constraint_failed")
        _values(self.params)


@dataclass(frozen=True)
class SqlRow:
    """Detached immutable row with unambiguous column names."""

    columns: tuple[str, ...]
    values: tuple[SqlValue, ...]

    def __post_init__(self) -> None:
        _values(self.values)
        if (
            type(self.columns) is not tuple
            or any(type(name) is not str for name in self.columns)
            or len(set(self.columns)) != len(self.columns)
            or len(self.columns) != len(self.values)
        ):
            raise DatabaseError("database_constraint_failed")

    def __getitem__(self, key: int | str) -> SqlValue:
        if isinstance(key, str):
            try:
                return self.values[self.columns.index(key)]
            except ValueError:
                raise KeyError(key) from None
        return self.values[key]


@dataclass(frozen=True)
class WriteResult:
    """Detached write metadata."""

    affected_rows: int | None
    last_insert_id: int | None


@dataclass(frozen=True)
class DatabaseIdentity:
    """Pinned physical identity; discovery wildcard is restricted to inspect."""

    store_id: str | None
    scope: Literal["project", "workplace"]
    owner_id: str

    def __post_init__(self) -> None:
        if (
            (
                self.store_id is not None
                and (
                    type(self.store_id) is not str
                    or re.fullmatch(r"[0-9a-f]{32}", self.store_id) is None
                )
            )
            or self.scope not in ("project", "workplace")
            or type(self.owner_id) is not str
            or not self.owner_id.strip()
            or "\x00" in self.owner_id
        ):
            raise DatabaseError("database_foreign")


@dataclass(frozen=True)
class DatabaseTarget:
    """An absolute target already resolved and authorized by the host."""

    path: Path
    identity: DatabaseIdentity

    def __post_init__(self) -> None:
        if (
            not isinstance(self.path, Path)
            or not self.path.is_absolute()
            or not isinstance(self.identity, DatabaseIdentity)
        ):
            raise DatabaseError("database_profile_invalid")


@dataclass(frozen=True)
class DatabaseCapabilities:
    """Capabilities advertised by a concrete driver."""

    transactions: bool
    read_snapshots: bool
    foreign_keys: bool
    transactional_ddl: bool
    online_backup: bool


class SqlSession(Protocol):
    """Operation/thread-bound repository DML and query access."""

    def fetch_one(self, statement: SqlStatement) -> SqlRow | None: ...

    def stream(
        self, statement: SqlStatement, *, batch_size: int = 256
    ) -> AbstractContextManager[Iterator[SqlRow]]: ...

    def execute(self, statement: SqlStatement) -> WriteResult: ...

    def execute_many(
        self, statement: SqlStatement, rows: Sequence[tuple[SqlValue, ...]]
    ) -> WriteResult: ...


class DatabaseDriver(Protocol):
    """Driver owns connection, transaction, identity and cleanup boundaries."""

    @property
    def capabilities(self) -> DatabaseCapabilities: ...

    def open(
        self,
        target: DatabaseTarget,
        *,
        mode: Literal["ro", "rw", "create"],
        timeout_ms: int,
        deadline: float | None = None,
    ) -> AbstractContextManager[SqlSession]: ...


class Database:
    """Cold binding. Reads and writes never create a missing store."""

    def __init__(
        self, driver: DatabaseDriver, target: DatabaseTarget, *, timeout_ms: int = 100
    ) -> None:
        if type(timeout_ms) is not int or not 0 <= timeout_ms <= 30000:
            raise DatabaseError("database_profile_invalid")
        self.driver = driver
        self.target = target
        self.timeout_ms = timeout_ms

    def read(
        self, *, deadline: float | None = None
    ) -> AbstractContextManager[SqlSession]:
        self._concrete()
        return self.driver.open(
            self.target, mode="ro", timeout_ms=self.timeout_ms, deadline=deadline
        )

    def transaction(
        self, *, deadline: float | None = None
    ) -> AbstractContextManager[SqlSession]:
        self._concrete()
        return self.driver.open(
            self.target, mode="rw", timeout_ms=self.timeout_ms, deadline=deadline
        )

    def _concrete(self) -> None:
        if self.target.identity.store_id is None:
            raise DatabaseError("database_foreign")
