"""Live YAML reads with bounded safe parsing reuse and legacy error semantics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ..common.request_scope import safe_load, safe_load_fields
from ..common.yaml_io import yaml_error


@dataclass(frozen=True)
class YamlDocumentReader:
    fallback: Callable[[str], dict[str, Any]]

    def load(self, path: Path) -> dict[str, Any]:
        return self._load(path, None)

    def load_fields(self, path: Path, fields: tuple[str, ...]) -> dict[str, Any]:
        return self._load(path, fields)

    def _load(self, path: Path, fields: tuple[str, ...] | None) -> dict[str, Any]:
        if not path.is_file():
            return {}
        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            data = safe_load(text) if fields is None else safe_load_fields(text, fields)
            return data if isinstance(data, dict) else {}
        except ModuleNotFoundError:
            data = self.fallback(text)
            return data if fields is None else {key: data[key] for key in fields if key in data}
        except Exception as exc:
            return {"__yaml_error__": f"{exc.__class__.__name__}: {exc}"}

    def read(self, path: Path) -> dict[str, Any]:
        data = self.load(path)
        error = data.get("__yaml_error__")
        if isinstance(error, str) and error:
            raise SystemExit(f"FAIL: {path} is invalid YAML: {error}")
        return data

    def policy(self, name: str, root: Path | None = None, *, distribution_root: Path) -> dict[str, Any]:
        path = (root or distribution_root) / "policies" / name
        if not path.is_file():
            return {}
        data = self.load(path)
        return data if isinstance(data, dict) and not yaml_error(data) else {}
