"""Local SQLite storage with explicit transactions and migration readiness."""

from __future__ import annotations

import sqlite3
import time
from contextlib import closing, contextmanager
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
    except BaseException as primary:
        try:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
        except BaseException as rollback_error:
            try:
                BaseException.add_note(
                    primary,
                    f"journal_rollback_failed: {type(rollback_error).__name__}; "
                    "transaction_outcome_unknown",
                )
            except BaseException:
                pass
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


def _enable_wal(connection: sqlite3.Connection) -> None:
    """Retry only WAL activation; SQLite can bypass its busy handler here."""
    with closing(connection.execute("PRAGMA journal_mode")) as cursor:
        if cursor.fetchone()[0].lower() == "wal":
            return
    with closing(connection.execute("PRAGMA busy_timeout")) as cursor:
        timeout = int(cursor.fetchone()[0])
    deadline = time.monotonic() + timeout / 1000
    remaining = timeout / 1000
    failure: BaseException | None = None
    try:
        while True:
            with closing(
                connection.execute(f"PRAGMA busy_timeout = {int(remaining * 1000)}")
            ):
                pass
            try:
                # Closing even a failed statement releases its promotion locks.
                with closing(connection.cursor()) as cursor:
                    mode = cursor.execute("PRAGMA journal_mode = WAL").fetchone()[0]
                if str(mode).lower() != "wal":
                    raise JournalError("journal_wal_unavailable")
                return
            except sqlite3.OperationalError as error:
                if getattr(error, "sqlite_errorcode", 0) & 0xFF != sqlite3.SQLITE_BUSY:
                    raise
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise
                time.sleep(min(0.005, remaining))
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise
    except BaseException as error:
        failure = error
        raise
    finally:
        try:
            with closing(connection.execute(f"PRAGMA busy_timeout = {timeout}")):
                pass
        except sqlite3.Error as restore_error:
            if failure is None:
                raise
            failure.add_note(f"journal_busy_timeout_restore_failed: {restore_error}")


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
    primary: BaseException | None = None
    try:
        connection.execute("PRAGMA busy_timeout = 10000")
        actual_id = connection.execute("PRAGMA application_id").fetchone()[0]
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        # These reads can straddle another initializer's commit. Either zero
        # requires the existing serialized recheck; only both zero below
        # authorize initialization of an empty store.
        if writable and (version == 0 or actual_id == 0):
            with transaction(connection):
                actual_id = connection.execute("PRAGMA application_id").fetchone()[0]
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if actual_id == 0 and version == 0:
                    if connection.execute(
                        "SELECT 1 FROM sqlite_master LIMIT 1"
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
            _enable_wal(connection)
            connection.execute("PRAGMA synchronous = FULL")
        yield connection
    except sqlite3.Error as exc:
        primary = JournalError("journal_database_error: " + str(exc))
        raise primary from exc
    except BaseException as exc:
        primary = exc
        raise
    finally:
        try:
            connection.close()
        except (sqlite3.Error, OSError) as cleanup:
            if primary is None:
                from .database.errors import DatabaseError
                from .database.sqlite import _failure

                if isinstance(cleanup, sqlite3.Error):
                    raise _failure(cleanup, None) from cleanup
                raise DatabaseError("database_io_failed") from cleanup
            primary.add_note(f"journal_close_failed: {type(cleanup).__name__}")


@contextmanager
def adapter_identity_access(
    path: Path,
    storage_host: StorageMigrationHost | None,
    *,
    writable: bool = False,
    migrating: bool = False,
) -> Iterator[tuple[StoreTarget, str] | None]:
    """Use the actual host-selected target and W4 gate; never discover an owner."""
    if storage_host is None:
        from .project.configuration_inputs import operation_storage_host

        storage_host = operation_storage_host(path, writable=writable)
    if storage_host is None:
        yield None
        return
    from .maintenance.contracts import MaintenanceError
    from .maintenance.storage_migration import (
        StorageMigrationHost,
        storage_identity_access,
    )

    try:
        selected_context = storage_host.context
    except MaintenanceError as error:
        if writable or error.code != "project_identity_required":
            raise
        from .project.configuration_inputs import verify_operation_legacy_read

        verify_operation_legacy_read(storage_host)
        # Missing stable identity prevents adoption, while the original
        # adapter still refuses any already-adopted envelope without its host.
        yield None
        return
    # Each adapter uses one immutable selection. A later adapter must ask the
    # automatic host again, since the previous operation may establish an owner.
    storage_host = StorageMigrationHost(
        selected_context, storage_host.service, _automatic=storage_host.automatic
    )
    targets = [target for target in selected_context.targets if target.target == path]
    if not targets and any(
        selected == path for _kind, selected in storage_host.context.unqualified_targets
    ):
        if writable:
            raise MaintenanceError("owner_identity_required")
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
    if migrating:
        # Explicit import may read its own importing barrier, but never ignores
        # a pending identity binding or a different owner/store.
        with storage_host.service._admit(selected_context, None):
            if storage_host.service.safety(selected_context).state != "proven":
                raise MaintenanceError("storage_offline_confirmation_required")
            with storage_identity_access(
                selected_context,
                target,
                registry_lock=storage_host.service.registry_lock,
                driver=storage_host.service.driver,
                allow_importing=True,
            ) as store_id:
                yield None if store_id is None else (target, store_id)
        return
    if writable:
        from .maintenance.fresh_project import ordinary_identity_access, owns_target

        if owns_target(storage_host, target):
            with ordinary_identity_access(storage_host, target) as identity:
                yield identity
            return
    if writable and path.exists() and storage_host.automatic:
        # Run adoption/recovery before any target gate or domain SQL session.
        from dataclasses import replace

        context = replace(storage_host.context, targets=(target,))
        report = storage_host.service.ensure_ready(context, trigger="first_write")
        if report.get("blocked"):
            raise MaintenanceError(
                str(
                    (report.get("error") or {}).get("code")
                    or "storage_activity_unknown"
                )
            )
    if writable and not path.exists():
        with storage_host.service.new_store_identity(
            storage_host.context, target
        ) as store_id:
            if store_id is None:
                raise MaintenanceError("storage_migration_required")
            yield target, store_id
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
            from .maintenance.storage_migration import (
                _descriptor,
                _inspect_target,
                _slot,
            )

            slot = _slot(root, target)
            if slot is not None:
                if slot["state"] != "ready":
                    raise MaintenanceError("storage_resume_required")
                facts = _inspect_target(
                    target,
                    _descriptor(verify_transforms=False),
                    storage_host.service.driver,
                )
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
            if writable and store_id is None:
                raise MaintenanceError("storage_migration_required")
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
        Path(path), storage_host, writable=writable, migrating=migrating
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
