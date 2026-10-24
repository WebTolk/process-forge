"""Immutable configuration values; no filesystem, YAML, host or CLI dependency."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, replace
from typing import Any

from .database import DatabaseConfig
from .errors import InvalidConfiguration


def _section(value: Any, fields: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) - fields:
        raise InvalidConfiguration("configuration_fields_invalid")
    return value


@dataclass(frozen=True)
class MetricsConfig:
    interval_seconds: float = 10.0

    def __post_init__(self) -> None:
        value = self.interval_seconds
        if (
            type(value) not in (int, float)
            or not 1 <= value <= 60
            or not math.isfinite(value)
        ):
            raise InvalidConfiguration("configuration_interval_invalid")


@dataclass(frozen=True)
class TemporaryFilesConfig:
    mode: str = "notify"
    max_age_hours: float = 168

    def __post_init__(self) -> None:
        _temporary_mode(self.mode)
        _temporary_age(self.max_age_hours)


def _temporary_mode(value: Any) -> None:
    if type(value) is not str or value not in {"notify", "off"}:
        raise InvalidConfiguration("configuration_temporary_files_mode_invalid")


def _temporary_age(value: Any) -> None:
    if (
        type(value) not in (int, float)
        or not 1 <= value <= 87600
        or not math.isfinite(value)
    ):
        raise InvalidConfiguration("configuration_temporary_files_age_invalid")


@dataclass(frozen=True)
class TemporaryFilesOverrides:
    mode: str | None = None
    max_age_hours: float | None = None

    def __post_init__(self) -> None:
        if self.mode is not None:
            _temporary_mode(self.mode)
        if self.max_age_hours is not None:
            _temporary_age(self.max_age_hours)


@dataclass(frozen=True)
class RuntimeConfig:
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    garage_hooks: bool = False
    temporary_files: TemporaryFilesConfig = field(default_factory=TemporaryFilesConfig)

    def __post_init__(self) -> None:
        if type(self.metrics) is not MetricsConfig:
            raise InvalidConfiguration("configuration_metrics_invalid")
        if type(self.garage_hooks) is not bool:
            raise InvalidConfiguration("configuration_garage_hooks_invalid")
        if type(self.temporary_files) is not TemporaryFilesConfig:
            raise InvalidConfiguration("configuration_temporary_files_invalid")


@dataclass(frozen=True)
class RuntimeOverrides:
    garage_hooks: bool | None = None
    temporary_files: TemporaryFilesOverrides = field(
        default_factory=TemporaryFilesOverrides
    )

    def __post_init__(self) -> None:
        if self.garage_hooks is not None and type(self.garage_hooks) is not bool:
            raise InvalidConfiguration("configuration_garage_hooks_invalid")
        if type(self.temporary_files) is not TemporaryFilesOverrides:
            raise InvalidConfiguration("configuration_temporary_files_invalid")


@dataclass(frozen=True)
class LoggingConfig:
    raw_hooks: bool = True
    events: bool = True

    def __post_init__(self) -> None:
        if type(self.raw_hooks) is not bool or type(self.events) is not bool:
            raise InvalidConfiguration("configuration_logging_invalid")


@dataclass(frozen=True)
class LoggingOverrides:
    raw_hooks: bool | None = None
    events: bool | None = None

    def __post_init__(self) -> None:
        for value in (self.raw_hooks, self.events):
            if value is not None and type(value) is not bool:
                raise InvalidConfiguration("configuration_logging_invalid")


def _get(value: dict, key: str) -> Any:
    if not isinstance(key, str) or not key:
        raise InvalidConfiguration("configuration_key_unknown")
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            raise InvalidConfiguration("configuration_key_unknown")
        value = value[part]
    return value


def _driver_change(value: dict, changes: dict[str, Any]) -> dict:
    if "database.driver" not in changes:
        return value
    database = dict(value.get("database", {}))
    selector = changes["database.driver"]
    if selector is None:
        database.pop("driver", None)
    else:
        database["driver"] = selector
    if database.get("profiles") or database.get("defaults") or "driver" in database:
        value["database"] = database
    else:
        value.pop("database", None)
    return value


def _with_changes(value: dict, changes: dict[str, Any], allowed: set[str]) -> dict:
    if not isinstance(changes, dict) or not changes:
        raise InvalidConfiguration("configuration_changes_empty")
    if "database" in changes and "database.driver" in changes:
        raise InvalidConfiguration("configuration_changes_invalid")
    for key in changes:
        if not isinstance(key, str) or key not in allowed:
            raise InvalidConfiguration("configuration_key_unknown")
    value = _driver_change(value, changes)
    for key, replacement in changes.items():
        if key == "database.driver":
            continue
        target = value
        parts = key.split(".")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = replacement
    return value


@dataclass(frozen=True)
class PFConfig:
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    schema_version: int = 1
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    database: DatabaseConfig | None = None

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise InvalidConfiguration("configuration_version_unsupported")
        if type(self.runtime) is not RuntimeConfig:
            raise InvalidConfiguration("configuration_runtime_invalid")
        if type(self.logging) is not LoggingConfig:
            raise InvalidConfiguration("configuration_logging_invalid")
        if self.database is not None and type(self.database) is not DatabaseConfig:
            raise InvalidConfiguration("database_profile_invalid")

    @classmethod
    def from_dict(cls, value: dict) -> PFConfig:
        root = _section(value, {"schema_version", "runtime", "logging", "database"})
        runtime = _section(
            root.get("runtime", {}), {"metrics", "garage_hooks", "temporary_files"}
        )
        metrics = _section(runtime.get("metrics", {}), {"interval_seconds"})
        temporary = _section(
            runtime.get("temporary_files", {}), {"mode", "max_age_hours"}
        )
        logging = _section(root.get("logging", {}), {"raw_hooks", "events"})
        return cls(
            runtime=RuntimeConfig(
                MetricsConfig(**metrics),
                runtime.get("garage_hooks", False),
                TemporaryFilesConfig(**temporary),
            ),
            schema_version=root.get("schema_version", 1),
            logging=LoggingConfig(**logging),
            database=DatabaseConfig.from_dict(root["database"])
            if "database" in root
            else None,
        )

    def to_dict(self) -> dict:
        value = {
            "runtime": asdict(self.runtime),
            "schema_version": self.schema_version,
            "logging": asdict(self.logging),
        }
        if self.database is not None:
            value["database"] = self.database.to_dict()
        return value

    def get(self, key: str) -> Any:
        if key == "database.driver":
            return (
                self.database.driver if self.database is not None else None
            ) or "sqlite"
        return _get(self.to_dict(), key)

    def with_changes(self, changes: dict[str, Any]) -> PFConfig:
        return self.from_dict(
            _with_changes(
                self.to_dict(),
                changes,
                {
                    "runtime.metrics.interval_seconds",
                    "runtime.garage_hooks",
                    "logging.raw_hooks",
                    "logging.events",
                    "runtime.temporary_files.mode",
                    "runtime.temporary_files.max_age_hours",
                    "database",
                    "database.driver",
                },
            )
        )

    def overlay(self, layer: PFConfig, *, explicit_keys: frozenset[str]) -> PFConfig:
        """Overlay only validated, explicitly present workplace leaves."""
        if type(layer) is not PFConfig or type(explicit_keys) is not frozenset:
            raise InvalidConfiguration("configuration_model_required")
        scalar_keys = {
            "runtime.metrics.interval_seconds",
            "runtime.garage_hooks",
            "runtime.temporary_files.mode",
            "runtime.temporary_files.max_age_hours",
            "logging.raw_hooks",
            "logging.events",
        }
        changes = {key: layer.get(key) for key in scalar_keys & explicit_keys}
        result = self.with_changes(changes) if changes else self
        source = layer.database
        if source is None:
            return result
        base = self.database or DatabaseConfig()
        profiles = dict(base.profiles)
        defaults = dict(base.defaults)
        for key, profile in source.profiles.items():
            if "database.profiles." + key in explicit_keys:
                if key in profiles:
                    raise InvalidConfiguration("database_profile_invalid")
                profiles[key] = profile
        for key, selected in source.defaults.items():
            if "database.defaults." + key in explicit_keys:
                defaults[key] = selected
        driver = base.driver
        if "database.driver" in explicit_keys and source.driver is not None:
            driver = source.driver
        if profiles or defaults or driver is not None or self.database is not None:
            result = replace(
                result, database=DatabaseConfig(profiles, defaults, driver)
            )
        return result

    def for_project(self, overrides: ProjectPFConfig) -> PFConfig:
        if type(overrides) is not ProjectPFConfig:
            raise InvalidConfiguration("configuration_project_model_required")
        values = {
            key: getattr(self.logging, key) if value is None else value
            for key, value in asdict(overrides.logging).items()
        }
        garage_hooks = overrides.runtime.garage_hooks
        runtime = (
            self.runtime
            if garage_hooks is None
            else replace(self.runtime, garage_hooks=garage_hooks)
        )
        temporary = {
            key: getattr(runtime.temporary_files, key) if value is None else value
            for key, value in asdict(overrides.runtime.temporary_files).items()
        }
        runtime = replace(runtime, temporary_files=TemporaryFilesConfig(**temporary))
        database = (
            overrides.database
            if self.database is None
            else self.database.for_project(overrides.database)
        )
        return replace(
            self, runtime=runtime, logging=LoggingConfig(**values), database=database
        )


@dataclass(frozen=True)
class ProjectPFConfig:
    """Explicit project overrides; null means inherit the workplace value."""

    logging: LoggingOverrides = field(default_factory=LoggingOverrides)
    schema_version: int = 1
    runtime: RuntimeOverrides = field(default_factory=RuntimeOverrides)
    database: DatabaseConfig | None = None

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise InvalidConfiguration("configuration_version_unsupported")
        if type(self.logging) is not LoggingOverrides:
            raise InvalidConfiguration("configuration_logging_invalid")
        if type(self.runtime) is not RuntimeOverrides:
            raise InvalidConfiguration("configuration_runtime_invalid")
        if self.database is not None:
            if type(self.database) is not DatabaseConfig:
                raise InvalidConfiguration("database_profile_invalid")
            self.database.require_project()

    @classmethod
    def from_dict(cls, value: dict) -> ProjectPFConfig:
        root = _section(value, {"schema_version", "logging", "runtime", "database"})
        logging = _section(root.get("logging", {}), {"raw_hooks", "events"})
        runtime = _section(root.get("runtime", {}), {"garage_hooks", "temporary_files"})
        temporary = _section(
            runtime.get("temporary_files", {}), {"mode", "max_age_hours"}
        )
        return cls(
            logging=LoggingOverrides(**logging),
            schema_version=root.get("schema_version", 1),
            runtime=RuntimeOverrides(
                runtime.get("garage_hooks"), TemporaryFilesOverrides(**temporary)
            ),
            database=DatabaseConfig.from_dict(root["database"], project=True)
            if "database" in root
            else None,
        )

    def to_dict(self) -> dict:
        value = {
            "logging": asdict(self.logging),
            "schema_version": self.schema_version,
            "runtime": asdict(self.runtime),
        }
        if self.database is not None:
            value["database"] = self.database.to_dict()
        return value

    def get(self, key: str) -> Any:
        if key == "database.driver":
            return self.database.driver if self.database is not None else None
        return _get(self.to_dict(), key)

    def with_changes(self, changes: dict[str, Any]) -> ProjectPFConfig:
        return self.from_dict(
            _with_changes(
                self.to_dict(),
                changes,
                {
                    "logging.raw_hooks",
                    "logging.events",
                    "runtime.garage_hooks",
                    "runtime.temporary_files.mode",
                    "runtime.temporary_files.max_age_hours",
                    "database",
                    "database.driver",
                },
            )
        )
