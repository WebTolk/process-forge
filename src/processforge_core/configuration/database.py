"""Immutable optional profiles; path authorization remains a host responsibility."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Any, Literal

from .errors import InvalidConfiguration


def _invalid() -> InvalidConfiguration:
    return InvalidConfiguration("database_profile_invalid")


@dataclass(frozen=True)
class DatabaseProfile:
    """A structural profile, with no filesystem access or implicit expansion."""

    scope: Literal["project", "workplace"]
    driver: Literal["sqlite"]
    path: str
    timeout_ms: int = 100

    def __post_init__(self) -> None:
        if (
            self.scope not in ("project", "workplace")
            or self.driver != "sqlite"
            or type(self.path) is not str
            or not self.path
            or type(self.timeout_ms) is not int
            or not 0 <= self.timeout_ms <= 30000
        ):
            raise _invalid()
        windows = PureWindowsPath(self.path)
        posix = PurePosixPath(self.path)
        parts = self.path.replace("\\", "/").split("/")
        if (
            windows.drive
            or windows.root
            or posix.is_absolute()
            or any(part in ("", ".", "..") for part in parts)
            or any(char in self.path for char in ("\x00", "$", "%", "~", ":"))
        ):
            raise _invalid()

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "driver": self.driver,
            "path": self.path,
            "timeout_ms": self.timeout_ms,
        }


@dataclass(frozen=True)
class DatabaseConfig:
    """Defensively copied immutable profile/default maps."""

    profiles: Mapping[str, DatabaseProfile]
    defaults: Mapping[str, str]

    def __post_init__(self) -> None:
        if not isinstance(self.profiles, Mapping) or not isinstance(
            self.defaults, Mapping
        ):
            raise _invalid()
        for key, profile in self.profiles.items():
            if (
                type(key) is not str
                or re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", key) is None
                or type(profile) is not DatabaseProfile
            ):
                raise _invalid()
        for key, profile_id in self.defaults.items():
            if (
                key not in ("project_main", "workplace_main")
                or type(profile_id) is not str
                or profile_id not in self.profiles
                or self.profiles[profile_id].scope != key.removesuffix("_main")
            ):
                raise _invalid()
        object.__setattr__(self, "profiles", MappingProxyType(dict(self.profiles)))
        object.__setattr__(self, "defaults", MappingProxyType(dict(self.defaults)))

    @classmethod
    def from_dict(cls, value: Any, *, project: bool = False) -> DatabaseConfig:
        if not isinstance(value, dict) or set(value) - {"profiles", "defaults"}:
            raise _invalid()
        profiles = value.get("profiles", {})
        defaults = value.get("defaults", {})
        if not isinstance(profiles, dict) or not isinstance(defaults, dict):
            raise _invalid()
        parsed: dict[str, DatabaseProfile] = {}
        for key, profile in profiles.items():
            if (
                not isinstance(profile, dict)
                or set(profile) - {"scope", "driver", "path", "timeout_ms"}
                or not {"scope", "driver", "path"} <= set(profile)
            ):
                raise _invalid()
            parsed[key] = DatabaseProfile(**profile)
        result = cls(parsed, defaults)
        if project:
            result.require_project()
        return result

    def require_project(self) -> None:
        if (
            any(profile.scope != "project" for profile in self.profiles.values())
            or "workplace_main" in self.defaults
        ):
            raise _invalid()

    def to_dict(self) -> dict[str, Any]:
        return {
            "profiles": {
                key: profile.to_dict() for key, profile in self.profiles.items()
            },
            "defaults": dict(self.defaults),
        }

    def for_project(self, overrides: DatabaseConfig | None) -> DatabaseConfig:
        if overrides is None:
            return self
        overrides.require_project()
        if self.profiles.keys() & overrides.profiles.keys():
            raise _invalid()
        return DatabaseConfig(
            dict(self.profiles) | dict(overrides.profiles),
            dict(self.defaults) | dict(overrides.defaults),
        )
