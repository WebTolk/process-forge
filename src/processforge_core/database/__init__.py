"""Public cold SQL API. Importing this package performs no storage operations."""

from .composition import DatabaseFactory
from .contracts import (
    Database,
    DatabaseCapabilities,
    DatabaseDriver,
    DatabaseIdentity,
    DatabaseTarget,
    SqlRow,
    SqlSession,
    SqlStatement,
    SqlValue,
    WriteResult,
)
from .errors import DatabaseError
from .schema import SchemaDefinition, SchemaManager, SchemaStatus
from .sqlite import SQLiteDriver

__all__ = [
    "Database",
    "DatabaseCapabilities",
    "DatabaseDriver",
    "DatabaseError",
    "DatabaseFactory",
    "DatabaseIdentity",
    "DatabaseTarget",
    "SchemaDefinition",
    "SchemaManager",
    "SchemaStatus",
    "SQLiteDriver",
    "SqlRow",
    "SqlSession",
    "SqlStatement",
    "SqlValue",
    "WriteResult",
]
