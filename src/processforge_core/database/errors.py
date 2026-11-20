"""Stable database failures without SQL, values, targets or native diagnostics."""


class DatabaseError(Exception):
    """Expose a machine-readable failure code and explicit retryability."""

    def __init__(self, code: str, retryable: bool = False) -> None:
        self.code = code
        self.retryable = retryable
        super().__init__(code)
