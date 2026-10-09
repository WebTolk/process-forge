"""Existing bounded Continuation control-document and path reads."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True, kw_only=True)
class ContinuationRecordReader:
    path_resolver: Callable[[], Callable[[str], Path]] = field(repr=False, compare=False)
    selector: Callable[[], Callable[[str], str]] = field(repr=False, compare=False)
    bounded_reader: Callable[[], Callable[[Path, int], bytes]] = field(repr=False, compare=False)
    yaml_loader: Callable[[], Callable[[str], Any]] = field(repr=False, compare=False)
    error: Callable[[], type[ValueError]] = field(repr=False, compare=False)

    def record_path(self, continuation_id: str) -> Path:
        return self.path_resolver()(".pf/continuations/" + self.selector()(continuation_id) + ".yaml")


    def selection_path(self, session_id: str) -> Path:
        if not isinstance(session_id, str) or not session_id or len(session_id) > 256:
            raise self.error()("invalid_session")
        return self.path_resolver()(".pf/continuations/selections/" + hashlib.sha256(session_id.encode()).hexdigest() + ".yaml")


    def load(self, path: Path) -> dict:
        if not path.exists():
            raise self.error()("continuation_not_found")
        data = self.yaml_loader()(self.bounded_reader()(path, 2 * 1024 * 1024).decode("utf-8-sig"))
        if not isinstance(data, dict):
            raise self.error()("continuation_state_invalid")
        return data
