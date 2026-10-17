"""Immutable configuration values; no filesystem, YAML, host or CLI dependency."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
import math
from typing import Any

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
        if type(value) not in (int, float) or not 1 <= value <= 60 or not math.isfinite(value):
            raise InvalidConfiguration("configuration_interval_invalid")


@dataclass(frozen=True)
class RuntimeConfig:
    metrics: MetricsConfig = field(default_factory=MetricsConfig)

    def __post_init__(self) -> None:
        if type(self.metrics) is not MetricsConfig:
            raise InvalidConfiguration("configuration_metrics_invalid")


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


def _with_changes(value: dict, changes: dict[str, Any], allowed: set[str]) -> dict:
    if not isinstance(changes, dict) or not changes:
        raise InvalidConfiguration("configuration_changes_empty")
    for key, replacement in changes.items():
        if not isinstance(key, str) or key not in allowed:
            raise InvalidConfiguration("configuration_key_unknown")
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

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise InvalidConfiguration("configuration_version_unsupported")
        if type(self.runtime) is not RuntimeConfig:
            raise InvalidConfiguration("configuration_runtime_invalid")
        if type(self.logging) is not LoggingConfig:
            raise InvalidConfiguration("configuration_logging_invalid")

    @classmethod
    def from_dict(cls, value: dict) -> PFConfig:
        root = _section(value, {"schema_version", "runtime", "logging"})
        runtime = _section(root.get("runtime", {}), {"metrics"})
        metrics = _section(runtime.get("metrics", {}), {"interval_seconds"})
        logging = _section(root.get("logging", {}), {"raw_hooks", "events"})
        return cls(runtime=RuntimeConfig(MetricsConfig(**metrics)), schema_version=root.get("schema_version", 1),
                   logging=LoggingConfig(**logging))

    def to_dict(self) -> dict:
        return asdict(self)

    def get(self, key: str) -> Any:
        return _get(self.to_dict(), key)

    def with_changes(self, changes: dict[str, Any]) -> PFConfig:
        return self.from_dict(_with_changes(self.to_dict(), changes, {
            "runtime.metrics.interval_seconds", "logging.raw_hooks", "logging.events",
        }))

    def for_project(self, overrides: ProjectPFConfig) -> PFConfig:
        if type(overrides) is not ProjectPFConfig:
            raise InvalidConfiguration("configuration_project_model_required")
        values = {key: getattr(self.logging, key) if value is None else value
                  for key, value in asdict(overrides.logging).items()}
        return replace(self, logging=LoggingConfig(**values))


@dataclass(frozen=True)
class ProjectPFConfig:
    """Only explicit logging overrides; null means inherit the device value."""
    logging: LoggingOverrides = field(default_factory=LoggingOverrides)
    schema_version: int = 1

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise InvalidConfiguration("configuration_version_unsupported")
        if type(self.logging) is not LoggingOverrides:
            raise InvalidConfiguration("configuration_logging_invalid")

    @classmethod
    def from_dict(cls, value: dict) -> ProjectPFConfig:
        root = _section(value, {"schema_version", "logging"})
        logging = _section(root.get("logging", {}), {"raw_hooks", "events"})
        return cls(logging=LoggingOverrides(**logging), schema_version=root.get("schema_version", 1))

    def to_dict(self) -> dict:
        return asdict(self)

    def get(self, key: str) -> Any:
        return _get(self.to_dict(), key)

    def with_changes(self, changes: dict[str, Any]) -> ProjectPFConfig:
        return self.from_dict(_with_changes(self.to_dict(), changes, {"logging.raw_hooks", "logging.events"}))
