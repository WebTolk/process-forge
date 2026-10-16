"""Atomic publication of the Runtime service's local JSON records."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
from typing import Any
import uuid


class RuntimeServiceStateWriter:
    """Prepare once; briefly retry only a Windows replacement conflict.

    The private 50 ms window limits retry admission and requested sleeps, not
    OS call duration or thread scheduling. Failed publication keeps its unique
    temporary file, as before, and never removes the destination.
    """

    def write(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self._replace(tmp, path)

    @staticmethod
    def _replace(tmp: Path, path: Path) -> None:
        try:
            os.replace(tmp, path)
            return
        except OSError as error:
            if sys.platform != "win32" or getattr(error, "winerror", None) not in {5, 32, 33}:
                raise
            original_error = error

        deadline = time.monotonic() + 0.05
        # The attempt cap also terminates a frozen/coarse clock. Preparation
        # and the payload are never repeated, even after multiple conflicts.
        for _ in range(5):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.01, remaining))
            if time.monotonic() >= deadline:
                break
            try:
                os.replace(tmp, path)
                return  # A successful OS call remains success past the deadline.
            except OSError as error:
                if getattr(error, "winerror", None) not in {5, 32, 33}:
                    raise
        raise original_error
