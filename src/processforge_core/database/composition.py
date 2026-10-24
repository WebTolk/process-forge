"""Cold closed driver mapping; profile selection never grants target access."""

from processforge_core.configuration.database import DatabaseConfig, DatabaseProfile

from .contracts import Database, DatabaseTarget
from .errors import DatabaseError
from .sqlite import SQLiteDriver


class DatabaseFactory:
    """Construct bindings from host-authorized targets without filesystem I/O."""

    @staticmethod
    def from_profile(
        config: DatabaseConfig | None,
        profile_id: str,
        authorized_target: DatabaseTarget,
    ) -> Database:
        if config is None:
            if profile_id != "project_main":
                raise DatabaseError("database_profile_invalid")
            profile = DatabaseProfile("project", "sqlite", "data/pf.sqlite3")
        else:
            try:
                profile = config.profiles[profile_id]
            except KeyError:
                raise DatabaseError("database_profile_invalid") from None
        if profile.driver != "sqlite":
            raise DatabaseError("database_driver_unsupported")
        if (
            authorized_target.identity.scope != profile.scope
            or authorized_target.identity.store_id is None
        ):
            raise DatabaseError("database_profile_invalid")
        # Containment and relative-path binding require a base and belong to host composition.
        return Database(
            SQLiteDriver(), authorized_target, timeout_ms=profile.timeout_ms
        )
