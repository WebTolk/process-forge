"""Revision-aware device/project configuration without host discovery."""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
import threading

from .errors import ConfigurationError, ConfigurationStorageError
from .models import PFConfig, ProjectPFConfig
from .storage import ConfigSnapshot
from .yaml_store import YamlConfigStore


@dataclass(frozen=True)
class ResolvedConfig:
    config: PFConfig
    device: ConfigSnapshot
    project: ConfigSnapshot
    errors: tuple[str, ...] = ()


class ConfigurationResolver:
    """Keep a bounded process-local snapshot, reload on file replacement.

    A failed later reload retains the last valid snapshot and its error code.
    First-load errors are reported rather than silently accepting bad config.
    """

    def __init__(self, *, max_entries: int = 128):
        if max_entries < 2:
            raise ValueError("configuration_cache_too_small")
        self.max_entries = max_entries
        self._entries = OrderedDict()
        self._lock = threading.RLock()

    @staticmethod
    def _signature(path: Path):
        try:
            value = path.lstat()
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise ConfigurationStorageError("configuration_read_failed") from exc
        return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
                value.st_mtime_ns, value.st_ctime_ns, getattr(value, "st_file_attributes", 0))

    def _read(self, path: Path, model):
        key = (str(path), model)
        previous = self._entries.get(key)
        signature = object()
        try:
            signature = self._signature(path)
            if previous is not None and previous[0] == signature:
                self._entries.move_to_end(key)
                return previous[1], previous[2]
            snapshot = YamlConfigStore(path, model=model).read()
            error = None
        except ConfigurationError as exc:
            if previous is None:
                raise
            snapshot, error = previous[1], exc.code
            # A stat failure is retried; invalid contents are retried on change.
        self._entries[key] = (signature, snapshot, error)
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)
        return snapshot, error

    def resolve(self, device_path: Path | None, project_path: Path) -> ResolvedConfig:
        with self._lock:
            if device_path is None:
                device, device_error = ConfigSnapshot(PFConfig(), None), None
            else:
                device, device_error = self._read(Path(device_path), PFConfig)
            project, project_error = self._read(Path(project_path), ProjectPFConfig)
            return ResolvedConfig(device.config.for_project(project.config), device, project,
                                  tuple(error for error in (device_error, project_error) if error))
