"""Stable configuration errors shared by all application interfaces."""


class ConfigurationError(ValueError):
    """A safe error code, without storage paths or configuration contents."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class InvalidConfiguration(ConfigurationError):
    pass


class ConfigurationConflict(ConfigurationError):
    pass


class ConfigurationStorageError(ConfigurationError):
    pass
