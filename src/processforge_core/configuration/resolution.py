"""Bound revision-aware application configuration without host discovery."""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .device import DeviceConfigurationSource
from .errors import ConfigurationError, ConfigurationStorageError, InvalidConfiguration
from .models import PFConfig, ProjectPFConfig
from .storage import ConfigSnapshot
from .yaml_store import YamlConfigStore


@dataclass(frozen=True)
class ResolvedConfig:
    """Effective value and exact immutable source snapshots."""

    config: PFConfig
    device: ConfigSnapshot
    project: ConfigSnapshot
    errors: tuple[str, ...] = ()
    workplace: ConfigSnapshot | None = None
    context_overrides: ProjectPFConfig | None = None


def _path(value: Path | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    if not path.is_absolute():
        raise ConfigurationStorageError("configuration_absolute_path_required")
    return path


class ConfigurationResolver:
    """Cache immutable sources; later read failure retains config and presence.

    First-load and merge errors propagate. Effective values are local to the
    exact selector tuple and are never cached by project identity or CWD.
    """

    def __init__(self, *, max_entries: int = 128):
        if max_entries < 2:
            raise ValueError("configuration_cache_too_small")
        self.max_entries = max_entries
        self._entries: OrderedDict[
            tuple[Path, type[PFConfig] | type[ProjectPFConfig]],
            tuple[object, ConfigSnapshot, str | None],
        ] = OrderedDict()
        self._lock = threading.RLock()

    @staticmethod
    def _signature(path: Path) -> object:
        try:
            value = path.lstat()
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise ConfigurationStorageError("configuration_read_failed") from exc
        return (
            value.st_dev,
            value.st_ino,
            value.st_mode,
            value.st_size,
            value.st_mtime_ns,
            value.st_ctime_ns,
            getattr(value, "st_file_attributes", 0),
        )

    def _read(
        self,
        path: Path,
        model: type[PFConfig] | type[ProjectPFConfig],
        *,
        refresh: bool,
    ) -> tuple[ConfigSnapshot, str | None]:
        _path(path)
        key = (path, model)
        previous = self._entries.get(key)
        signature = object()
        try:
            signature = self._signature(path)
            if not refresh and previous is not None and previous[0] == signature:
                self._entries.move_to_end(key)
                return previous[1], previous[2]
            snapshot = YamlConfigStore(path, model=model).read()
            error = None
        except ConfigurationError as exc:
            if previous is None:
                raise
            snapshot, error = previous[1], exc.code
        self._entries[key] = (signature, snapshot, error)
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)
        return snapshot, error

    def resolve(
        self,
        device_path: Path | None,
        project_path: Path | None,
        *,
        workplace_path: Path | None = None,
        context_overrides: ProjectPFConfig | None = None,
        refresh: bool = False,
    ) -> ResolvedConfig:
        """Resolve builtin/device/workplace/project/authorized typed context.

        The original two positional arguments keep their base/project meaning.
        A None device means builtin here; only the provider chooses a default.
        """
        if (
            context_overrides is not None
            and type(context_overrides) is not ProjectPFConfig
        ):
            raise InvalidConfiguration("configuration_project_model_required")
        with self._lock:
            device, device_error = (
                (ConfigSnapshot(PFConfig(), None), None)
                if device_path is None
                else self._read(Path(device_path), PFConfig, refresh=refresh)
            )
            project, project_error = (
                (ConfigSnapshot(ProjectPFConfig(), None), None)
                if project_path is None
                else self._read(Path(project_path), ProjectPFConfig, refresh=refresh)
            )
            workplace, workplace_error = (
                (None, None)
                if workplace_path is None
                else self._read(Path(workplace_path), PFConfig, refresh=refresh)
            )
            assert isinstance(device.config, PFConfig)
            assert isinstance(project.config, ProjectPFConfig)
            config = device.config
            if workplace is not None:
                assert isinstance(workplace.config, PFConfig)
                config = config.overlay(
                    workplace.config, explicit_keys=workplace.explicit_keys
                )
            config = config.for_project(project.config)
            if context_overrides is not None:
                config = config.for_project(context_overrides)
            return ResolvedConfig(
                config,
                device,
                project,
                tuple(
                    error
                    for error in (device_error, workplace_error, project_error)
                    if error
                ),
                workplace,
                context_overrides,
            )


@dataclass(frozen=True, init=False, eq=False)
class ConfigurationProvider:
    """Immutable selectors or a pinned operation/attempt snapshot.

    Construction is cold. Hosts read once per operation and pin downstream.
    """

    device_path: Path | None
    workplace_path: Path | None
    project_path: Path | None
    context_overrides: ProjectPFConfig | None
    _resolver: ConfigurationResolver | None = field(repr=False, compare=False)
    _pinned: ResolvedConfig | None = field(repr=False, compare=False)

    def __init__(
        self,
        *,
        device_path: Path | None = None,
        workplace_path: Path | None = None,
        project_path: Path | None = None,
        context_overrides: ProjectPFConfig | None = None,
        resolver: ConfigurationResolver | None = None,
    ):
        if (
            context_overrides is not None
            and type(context_overrides) is not ProjectPFConfig
        ):
            raise InvalidConfiguration("configuration_project_model_required")
        object.__setattr__(
            self,
            "device_path",
            _path(
                device_path
                if device_path is not None
                else DeviceConfigurationSource.default_path()
            ),
        )
        object.__setattr__(self, "workplace_path", _path(workplace_path))
        object.__setattr__(self, "project_path", _path(project_path))
        object.__setattr__(self, "context_overrides", context_overrides)
        object.__setattr__(
            self,
            "_resolver",
            resolver if resolver is not None else ConfigurationResolver(),
        )
        object.__setattr__(self, "_pinned", None)

    def snapshot(self, *, refresh: bool = False) -> ResolvedConfig:
        """Read the bound sources or return the same pinned object without I/O."""
        if self._pinned is not None:
            return self._pinned
        assert self._resolver is not None
        return self._resolver.resolve(
            self.device_path,
            self.project_path,
            workplace_path=self.workplace_path,
            context_overrides=self.context_overrides,
            refresh=refresh,
        )

    def current(self) -> PFConfig:
        """Return the complete effective application value."""
        return self.snapshot().config

    def get(self, key: str) -> Any:
        """Read a typed parameter from the effective value."""
        return self.current().get(key)

    @classmethod
    def pinned(
        cls, config: PFConfig, *, errors: tuple[str, ...] = ()
    ) -> ConfigurationProvider:
        """Pin a resolved native value without discovery, environment or reads."""
        if (
            type(config) is not PFConfig
            or type(errors) is not tuple
            or any(type(code) is not str for code in errors)
        ):
            raise InvalidConfiguration("configuration_model_required")
        provider = object.__new__(cls)
        for key in (
            "device_path",
            "workplace_path",
            "project_path",
            "context_overrides",
            "_resolver",
        ):
            object.__setattr__(provider, key, None)
        object.__setattr__(
            provider,
            "_pinned",
            ResolvedConfig(
                config,
                ConfigSnapshot(config, None),
                ConfigSnapshot(ProjectPFConfig(), None),
                errors,
            ),
        )
        return provider
