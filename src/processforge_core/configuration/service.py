"""Configuration use cases independent of storage and application interface."""
from __future__ import annotations

from typing import Any

from .errors import ConfigurationConflict
from .models import PFConfig
from .storage import ConfigSnapshot, ConfigStore


class ConfigService:
    def __init__(self, store: ConfigStore):
        self._store = store

    def read(self) -> ConfigSnapshot:
        return self._store.read()

    def create(self, config: PFConfig | None = None) -> ConfigSnapshot:
        return self._store.write(config if config is not None else PFConfig(), expected_revision=None)

    def _existing(self, expected_revision: str | None) -> ConfigSnapshot:
        current = self.read()
        if not current.exists:
            raise ConfigurationConflict("configuration_missing")
        if expected_revision is not None and expected_revision != current.revision:
            raise ConfigurationConflict("configuration_revision_conflict")
        return current

    def update(self, changes: dict[str, Any], *, expected_revision: str | None = None) -> ConfigSnapshot:
        current = self._existing(expected_revision)
        return self._store.write(current.config.with_changes(changes), expected_revision=current.revision)

    def reset(self, key: str, *, expected_revision: str | None = None) -> ConfigSnapshot:
        return self.update({key: PFConfig().get(key)}, expected_revision=expected_revision)

    def delete(self, *, expected_revision: str | None = None) -> ConfigSnapshot:
        current = self._existing(expected_revision)
        return self._store.delete(expected_revision=current.revision)
