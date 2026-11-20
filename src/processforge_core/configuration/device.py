"""Declared device configuration location without filesystem discovery."""

import os
from pathlib import Path

from .errors import ConfigurationStorageError


class DeviceConfigurationSource:
    """Select the full application source once for a host session."""

    @staticmethod
    def default_path() -> Path:
        """Return the declared absolute platform path without creating it."""
        if os.name == "nt":
            selected = os.environ.get("LOCALAPPDATA")
            base = Path(selected) if selected else Path.home() / "AppData" / "Local"
            suffix = Path("ProcessForge") / "configuration.yaml"
        else:
            selected = os.environ.get("XDG_CONFIG_HOME")
            base = Path(selected) if selected else Path.home() / ".config"
            suffix = Path("processforge") / "configuration.yaml"
        if not base.is_absolute():
            raise ConfigurationStorageError("configuration_absolute_path_required")
        return base / suffix
