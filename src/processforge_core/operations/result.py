"""Result of one native action and its invocation-local output."""

from dataclasses import dataclass
from typing import TextIO


@dataclass(frozen=True)
class NativeResult:
    """Result passed to the Runtime transport."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    value: object = None

    @property
    def output(self) -> str:
        return self.stdout + self.stderr


class CommandOutput:
    """Send text to the caller's stream and retain the application value."""

    def __init__(self, stream: TextIO | None) -> None:
        self._stream = stream
        self.value: object = None

    def write(self, value: object, *, end: str = "\n") -> None:
        if self._stream is not None:
            print(value, end=end, file=self._stream)
