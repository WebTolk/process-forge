"""Existing raw-byte file digests shared by concrete Core readers."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path


@dataclass(frozen=True)
class FileDigestReader:
    def sha256_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def sha256_bytes(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def sha256_optional_file(self, path: Path) -> str | None:
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
