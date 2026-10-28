"""Explicit-path YAML adapter with bounded reads, OS locking and atomic writes."""

from __future__ import annotations

import hashlib
import io
import os
import stat
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypeVar, cast

import yaml

from .errors import (
    ConfigurationConflict,
    ConfigurationStorageError,
    InvalidConfiguration,
)
from .models import PFConfig, ProjectPFConfig
from .storage import ConfigSnapshot

MAX_BYTES = 65536
_Config = TypeVar("_Config", bound=PFConfig | ProjectPFConfig)


class _Loader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in result:
                raise InvalidConfiguration("configuration_duplicate_or_invalid_key")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def _presence(value: dict[str, Any], prefix: str = "") -> frozenset[str]:
    """Collect leaves from the same validated mapping; profiles are atomic."""
    keys: set[str] = set()
    for key, item in value.items():
        dotted = prefix + key
        if dotted == "schema_version":
            continue
        if prefix == "database.profiles." or not isinstance(item, dict):
            keys.add(dotted)
        else:
            keys.update(_presence(item, dotted + "."))
    return frozenset(keys)


class YamlConfigStore:
    """No workplace discovery or directory creation; caller supplies the target."""

    def __init__(
        self, path: Path, *, model: type[PFConfig] | type[ProjectPFConfig] = PFConfig
    ):
        self.path = Path(path)
        if model not in (PFConfig, ProjectPFConfig):
            raise InvalidConfiguration("configuration_model_required")
        self.model = model
        if not self.path.is_absolute():
            raise ConfigurationStorageError("configuration_absolute_path_required")

    @staticmethod
    def _revision(raw: bytes | None) -> str | None:
        return None if raw is None else "sha256:" + hashlib.sha256(raw).hexdigest()

    def _check_path(self, path: Path) -> bool:
        if path.parent.resolve() != path.parent:
            raise ConfigurationStorageError("configuration_unsafe_path")
        try:
            info = path.lstat()
        except FileNotFoundError:
            return False
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or getattr(info, "st_file_attributes", 0) & 0x400
        ):
            raise ConfigurationStorageError("configuration_unsafe_path")
        return True

    def _raw(self) -> bytes | None:
        if not self._check_path(self.path):
            captured_path = getattr(io.open, "_pf_captured_path", None)
            if captured_path is None or not captured_path(self.path):
                return None
        try:
            with self.path.open("rb") as stream:
                raw = stream.read(MAX_BYTES + 1)
        except FileNotFoundError:
            return None
        if len(raw) > MAX_BYTES:
            raise InvalidConfiguration("configuration_oversize")
        return raw

    @staticmethod
    def _decode(raw: bytes | None) -> PFConfig:
        return YamlConfigStore._decode_model(raw, PFConfig)

    @staticmethod
    def _decode_model(raw: bytes | None, model: type[_Config]) -> _Config:
        return YamlConfigStore._decoded(raw, model)[0]

    @staticmethod
    def _decoded(
        raw: bytes | None, model: type[_Config]
    ) -> tuple[_Config, frozenset[str]]:
        if raw is None:
            return model(), frozenset()
        try:
            text = raw.decode("utf-8-sig")
            if any(
                isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken))
                for token in yaml.scan(text)
            ):
                raise InvalidConfiguration("configuration_alias_forbidden")
            value = yaml.load(text, Loader=_Loader)
            config = cast(_Config, model.from_dict(value))
            return config, _presence(value)
        except (UnicodeError, yaml.YAMLError, RecursionError) as exc:
            raise InvalidConfiguration("configuration_yaml_invalid") from exc

    def read(self) -> ConfigSnapshot:
        try:
            raw = self._raw()
            config, explicit_keys = self._decoded(raw, self.model)
            return ConfigSnapshot(config, self._revision(raw), explicit_keys)
        except OSError as exc:
            raise ConfigurationStorageError("configuration_read_failed") from exc

    @contextmanager
    def _lock(self):
        path = self.path.with_name(self.path.name + ".lock")
        self._check_path(path)
        # Never unlink the lock inode: waiters must keep using the same lock.
        with path.open("a+b") as stream:
            if stream.seek(0, 2) == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            try:
                if sys.platform == "win32":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise ConfigurationConflict("configuration_writer_busy") from exc
            try:
                yield
            finally:
                stream.seek(0)
                if sys.platform == "win32":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def _compare(self, expected_revision: str | None) -> None:
        if self._revision(self._raw()) != expected_revision:
            raise ConfigurationConflict("configuration_revision_conflict")

    def _sync_directory(self) -> None:
        if sys.platform != "win32":
            fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)

    def write(
        self, config: PFConfig | ProjectPFConfig, *, expected_revision: str | None
    ) -> ConfigSnapshot:
        if type(config) is not self.model:
            raise InvalidConfiguration("configuration_model_required")
        raw = yaml.safe_dump(
            config.to_dict(), sort_keys=False, allow_unicode=True
        ).encode("utf-8")
        staged = None
        try:
            with self._lock():
                self._compare(expected_revision)
                mode = (
                    stat.S_IMODE(self.path.stat().st_mode)
                    if self.path.exists()
                    else 0o600
                )
                from processforge_platforms.file_security import native_file_security

                security = native_file_security()
                descriptor = (
                    security.descriptor(self.path) if self.path.exists() else None
                )
                fd, name = tempfile.mkstemp(
                    prefix=".configuration-", suffix=".tmp", dir=self.path.parent
                )
                staged = Path(name)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                if descriptor is not None:
                    security.restore(staged, descriptor)
                self._compare(expected_revision)
                if descriptor is not None:
                    # ReplaceFileW merges ACLs and can clear inherited control
                    # bits. Rename the already verified descriptor with the data.
                    os.replace(staged, self.path)
                else:
                    security.replace(self.path, staged, mode)
                self._sync_directory()
                validated, explicit_keys = self._decoded(raw, self.model)
                return ConfigSnapshot(validated, self._revision(raw), explicit_keys)
        except OSError as exc:
            raise ConfigurationStorageError("configuration_write_failed") from exc
        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)

    def delete(self, *, expected_revision: str) -> ConfigSnapshot:
        if expected_revision is None:
            raise ConfigurationConflict("configuration_missing")
        try:
            with self._lock():
                self._compare(expected_revision)
                self.path.unlink()
                self._sync_directory()
                return ConfigSnapshot(self.model(), None)
        except OSError as exc:
            raise ConfigurationStorageError("configuration_delete_failed") from exc
