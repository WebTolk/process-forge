"""Local SQLite storage with explicit transactions and migration readiness."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from .maintenance.contracts import StoreTarget
    from .maintenance.storage_migration import StorageMigrationHost


from .database import DatabaseFactory, SQLiteDriver


class JournalError(RuntimeError):
    """A private journal could not be used safely."""


class JournalMigrationRequired(JournalError):
    """The legacy journal needs an explicit, completed import."""


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    connection.execute("BEGIN IMMEDIATE")
    try:
        yield connection
        connection.execute("COMMIT")
    except BaseException:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise


def metadata(connection: sqlite3.Connection, key: str) -> str | None:
    row = connection.execute(
        "SELECT value FROM journal_metadata WHERE key = ?", (key,)
    ).fetchone()
    return str(row[0]) if row is not None else None


def set_metadata(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        "INSERT INTO journal_metadata(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


@contextmanager
def _database(
    path: Path,
    *,
    application_id: int,
    schema: tuple[str, ...],
    writable: bool = False,
    migrating: bool = False,
    legacy_path: Path | None = None,
    driver: SQLiteDriver | None = None,
    identity: tuple[StoreTarget, str] | None = None,
) -> Iterator[sqlite3.Connection]:
    """Always close the operation-local connection in its calling thread.

    WAL and FULL commits retain durable acceptance. Read-only operations do
    not create a missing file or initialize its schema.
    """
    path = Path(path)
    if path.is_symlink():
        raise JournalError("journal_unsafe_path")
    legacy_exists = (
        legacy_path is not None
        and legacy_path.is_file()
        and legacy_path.stat().st_size > 0
    )
    if not path.is_file():
        if not writable:
            if legacy_exists:
                raise JournalMigrationRequired(
                    "journal_migration_required: run tools/migrate-hook-journals.py"
                )
            raise FileNotFoundError(path.name)
        if legacy_exists and not migrating:
            raise JournalMigrationRequired(
                "journal_migration_required: run tools/migrate-hook-journals.py"
            )
        path.parent.mkdir(parents=True, exist_ok=True)
    target = str(path) if writable else path.resolve().as_uri() + "?mode=ro"
    try:
        connection = (
            driver if driver is not None else DatabaseFactory.resolve_driver()
        )._connect(target, timeout=10.0, isolation_level=None, uri=not writable)
    except sqlite3.Error as exc:
        raise JournalError("journal_database_error: " + str(exc)) from exc
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA busy_timeout = 10000")
        actual_id = connection.execute("PRAGMA application_id").fetchone()[0]
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version == 0 and actual_id == 0 and writable:
            with transaction(connection):
                actual_id = connection.execute("PRAGMA application_id").fetchone()[0]
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if actual_id == 0 and version == 0:
                    if connection.execute(
                        "SELECT 1 FROM sqlite_master WHERE type = 'table' LIMIT 1"
                    ).fetchone():
                        raise JournalError("journal_schema_unrecognized")
                    connection.execute(
                        "CREATE TABLE journal_metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
                    )
                    for statement in schema:
                        connection.execute(statement)
                    set_metadata(connection, "history_count", "0")
                    set_metadata(
                        connection,
                        "migration_state",
                        "importing" if migrating else "ready",
                    )
                    connection.execute(f"PRAGMA application_id = {int(application_id)}")
                    connection.execute("PRAGMA user_version = 1")
                    if identity is not None:
                        from .maintenance.storage_migration import add_store_identity

                        add_store_identity(connection, *identity)
                    actual_id, version = application_id, 1
        if (
            identity is None
            and connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name='pf_store_meta'"
            ).fetchone()
        ):
            raise JournalError("storage_host_required")
        if actual_id != application_id or version != 1:
            raise JournalError("journal_schema_unsupported")
        if not migrating:
            if metadata(connection, "migration_state") != "ready":
                raise JournalMigrationRequired("journal_migration_incomplete")
            if legacy_exists and metadata(connection, "legacy_imported") != "1":
                raise JournalMigrationRequired(
                    "journal_migration_required: run tools/migrate-hook-journals.py"
                )
        if writable:
            if connection.execute("PRAGMA journal_mode").fetchone()[0].lower() != "wal":
                connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = FULL")
        yield connection
    except sqlite3.Error as exc:
        raise JournalError("journal_database_error: " + str(exc)) from exc
    finally:
        connection.close()


@contextmanager
def adapter_identity_access(
    path: Path, storage_host: StorageMigrationHost | None, *, writable: bool = False
) -> Iterator[tuple[StoreTarget, str] | None]:
    """Use the actual host-selected target and W4 gate; never discover an owner."""
    if storage_host is None:
        from .project.configuration_inputs import operation_storage_host

        storage_host = operation_storage_host(path)
    if storage_host is None:
        yield None
        return
    from .maintenance.contracts import MaintenanceError
    from .maintenance.storage_migration import storage_identity_access

    try:
        selected_context = storage_host.context
    except MaintenanceError as error:
        if error.code != "project_identity_required":
            raise
        # Missing stable identity prevents adoption, while the original
        # adapter still refuses any already-adopted envelope without its host.
        yield None
        return
    targets = [
        target for target in selected_context.targets if target.target == path
    ]
    if not targets and any(
        selected == path for _kind, selected in storage_host.context.unqualified_targets
    ):
        from .maintenance.storage_migration import _descriptor

        # Qualified layout and no metadata/pending pin are required even when
        # the old workplace has no stable owner ID. No owner is fabricated.
        storage_host.service._unqualified(
            storage_host.context, _descriptor(verify_transforms=False)
        )
        yield None
        return
    if len(targets) != 1 or targets[0].kind == "main":
        raise MaintenanceError("storage_target_invalid")
    target = targets[0]
    if writable and path.exists() and storage_host.automatic:
        # Run adoption/recovery before any target gate or domain SQL session.
        from dataclasses import replace

        context = replace(storage_host.context, targets=(target,))
        report = storage_host.service.ensure_ready(context, trigger="first_write")
        if report.get("blocked") and not any(
            item.get("target_relative_path") == target.target_relative_path
            and item.get("state") == "deferred"
            and item.get("legacy_allowed") is True
            for item in report.get("targets", ())
        ):
            raise MaintenanceError(
                str(
                    (report.get("error") or {}).get("code")
                    or "storage_activity_unknown"
                )
            )
    if writable and not path.exists():
        with storage_host.service.new_store_identity(
            storage_host.context, target, _allow_legacy=True
        ) as store_id:
            yield None if store_id is None else (target, store_id)
    else:
        root = (
            storage_host.context.workplace_root
            if target.scope == "workplace"
            else storage_host.context.project_root / ".pf"
            if storage_host.context.project_root is not None
            else None
        )
        if (
            not writable
            and root is not None
            and not (root / "runtime/.storage-identity.lock.guard").exists()
        ):
            # An unadopted read must not create the identity guard. The domain
            # adapter still rejects unexpected metadata; migration always
            # creates the permanent guard before publishing pending state.
            from .maintenance.storage_migration import _descriptor, _inspect_target, _slot

            slot = _slot(root, target)
            if slot is not None:
                if slot["state"] != "ready":
                    raise MaintenanceError("storage_resume_required")
                facts = _inspect_target(target, _descriptor(verify_transforms=False), storage_host.service.driver)
                if facts.get("store_id") != slot["store_id"]:
                    raise MaintenanceError("storage_identity_conflict")
            yield None if slot is None else (target, str(slot["store_id"]))
            return
        with storage_identity_access(
            storage_host.context,
            target,
            registry_lock=storage_host.service.registry_lock,
            driver=storage_host.service.driver,
        ) as store_id:
            yield None if store_id is None else (target, store_id)


@contextmanager
def database(
    path: Path,
    *,
    application_id: int,
    schema: tuple[str, ...],
    writable: bool = False,
    migrating: bool = False,
    legacy_path: Path | None = None,
    driver: SQLiteDriver | None = None,
    storage_host: StorageMigrationHost | None = None,
) -> Iterator[sqlite3.Connection]:
    """Hold identity admission until the legacy connection is closed."""
    with adapter_identity_access(
        Path(path), storage_host, writable=writable
    ) as identity:
        with _database(
            path,
            application_id=application_id,
            schema=schema,
            writable=writable,
            migrating=migrating,
            legacy_path=legacy_path,
            driver=driver,
            identity=identity,
        ) as connection:
            yield connection
