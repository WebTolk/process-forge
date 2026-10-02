"""Immutable configuration values; no filesystem, YAML, host or CLI dependency."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
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
class PFConfig:
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    schema_version: int = 1

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise InvalidConfiguration("configuration_version_unsupported")
        if type(self.runtime) is not RuntimeConfig:
            raise InvalidConfiguration("configuration_runtime_invalid")

    @classmethod
    def from_dict(cls, value: dict) -> PFConfig:
        root = _section(value, {"schema_version", "runtime"})
        runtime = _section(root.get("runtime", {}), {"metrics"})
        metrics = _section(runtime.get("metrics", {}), {"interval_seconds"})
        return cls(runtime=RuntimeConfig(MetricsConfig(**metrics)), schema_version=root.get("schema_version", 1))

    def to_dict(self) -> dict:
        return asdict(self)

    def get(self, key: str) -> Any:
        if not isinstance(key, str) or not key:
            raise InvalidConfiguration("configuration_key_unknown")
        value = self.to_dict()
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                raise InvalidConfiguration("configuration_key_unknown")
            value = value[part]
        return value

    def with_changes(self, changes: dict[str, Any]) -> PFConfig:
        if not isinstance(changes, dict) or not changes:
            raise InvalidConfiguration("configuration_changes_empty")
        value = self.to_dict()
        for key, replacement in changes.items():
            if not isinstance(key, str) or key != "runtime.metrics.interval_seconds":
                raise InvalidConfiguration("configuration_key_unknown")
            value["runtime"]["metrics"]["interval_seconds"] = replacement
        return self.from_dict(value)
