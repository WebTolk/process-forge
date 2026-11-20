from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

from .documents import UpdateDocumentReader
from .sites import UpdateSitePolicy


class UpdateTransferService:
    """Fetch update manifests and copy or download their artifacts."""

    def __init__(self, distribution_root: Path) -> None:
        self.site_policy = UpdateSitePolicy()
        self.documents = UpdateDocumentReader(distribution_root)

    def manifest(self, source: dict[str, Any], workplace_root: Path) -> tuple[dict[str, Any], list[str]]:
        warnings: list[str] = []
        location = self.site_policy.location(source, "provider")
        if not location:
            return {}, ["missing manifest_url"]
        parsed = urlparse(location)
        scheme = parsed.scheme.lower()
        if scheme == "file" or not scheme:
            path = self.documents.file_url_path(location, workplace_root)
            data = self.documents.document(path)
            if not data:
                return {}, [f"manifest not found or invalid: {path}"]
            return data, warnings
        if scheme in {"http", "https"}:
            try:
                with urlopen(location, timeout=15) as response:
                    text = response.read().decode("utf-8")
            except Exception as exc:
                return {}, [f"manifest fetch failed: {exc}"]
            data = self.documents.text(text)
            if not data:
                return {}, [f"manifest response invalid: {location}"]
            return data, warnings
        return {}, [f"manifest_url scheme is unsupported: {scheme}"]

    def artifact(self, candidate: dict[str, Any], target: Path, workplace_root: Path) -> Path:
        url = str(candidate.get("download_url") or "")
        if not url:
            raise ValueError("candidate has no download_url")
        parsed = urlparse(url)
        if parsed.scheme in {"", "file"}:
            source = self.documents.file_url_path(url, workplace_root)
            if not source.is_file():
                raise FileNotFoundError(source)
            target_name = source.name
            destination = target / target_name
            shutil.copy2(source, destination)
            return destination
        if parsed.scheme in {"http", "https"}:
            destination = target / Path(parsed.path).name
            with urlopen(url, timeout=30) as response, destination.open("wb") as output:
                shutil.copyfileobj(response, output)
            return destination
        raise ValueError(f"unsupported artifact URL scheme: {parsed.scheme}")
