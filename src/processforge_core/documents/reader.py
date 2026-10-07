"""Live YAML reads with request-local safe parsing and legacy error semantics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ..request_scope import safe_load


@dataclass(frozen=True)
class YamlDocumentReader:
    fallback: Callable[[str], dict[str, Any]]

    def load(self, path: Path) -> dict[str, Any]:
        if not path.is_file():
            return {}
        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            data = safe_load(text)
            return data if isinstance(data, dict) else {}
        except ModuleNotFoundError:
            return self.fallback(text)
        except Exception as exc:
            return {"__yaml_error__": f"{exc.__class__.__name__}: {exc}"}

    def read(self, path: Path) -> dict[str, Any]:
        data = self.load(path)
        error = data.get("__yaml_error__")
        if isinstance(error, str) and error:
            raise SystemExit(f"FAIL: {path} is invalid YAML: {error}")
        return data
