"""Existing release-manifest validation and archive-member path policy."""

from __future__ import annotations

import hashlib
import re
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from processforge_core.common.checks import Check, check
from processforge_core.common.digests import FileDigestReader
from processforge_core.common.release_identity import HEX64_RE, RELEASE_NAME
import processforge_core.maintenance.release_provenance as release_provenance


class ReleaseManifestPolicy:
    def __init__(self, file_digests: FileDigestReader) -> None:
        self._file_digests = file_digests

    def release_manifest_path_error(self, name: str) -> str | None:
        if not name or "\x00" in name or any(ord(char) < 32 for char in name):
            return "empty, NUL, or control-character archive path"
        normalized = name.replace("\\", "/")
        if "\\" in name:
            return "archive path contains backslash"
        if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized) or normalized.startswith("//"):
            return "absolute, drive-qualified, or UNC archive path"
        parts = normalized.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            return "archive path contains empty, current, or parent segment"
        if Path(normalized).is_absolute():
            return "absolute archive path"
        return None

    def validate_release_manifest_contract(
        self,
        data: Any,
        archive_path: Path,
        infos: list[zipfile.ZipInfo],
    ) -> list[Check]:
        checks: list[Check] = []
        actual_size = archive_path.stat().st_size
        actual_sha = self._file_digests.sha256_file(archive_path)
        if not isinstance(data, dict):
            return [check("FAIL", "release manifest v1 is an object")]
        top_keys = {"schema_version", "name", "version", "schema_bundle_version", "release_eligible", "build", "source", "archive", "official_packs", "files"}
        unexpected = sorted(set(data) - top_keys)
        missing = sorted(top_keys - set(data))
        checks.append(check("PASS" if not unexpected else "FAIL", "release manifest v1 has no unexpected top-level keys"))
        checks.append(check("PASS" if not missing else "FAIL", "release manifest v1 required keys present"))
        for key in unexpected[:10]:
            checks.append(check("FAIL", f"release manifest unexpected key: {key}"))
        for key in missing[:10]:
            checks.append(check("FAIL", f"release manifest missing key: {key}"))
        checks.append(check("PASS" if data.get("schema_version") == 1 else "FAIL", "release manifest schema_version is 1"))
        checks.append(check("PASS" if data.get("name") == RELEASE_NAME else "FAIL", "release manifest name is processforge"))
        checks.append(check("PASS" if data.get("release_eligible") is True else "FAIL", "release manifest marks public release eligible"))

        build = data.get("build") if isinstance(data.get("build"), dict) else {}
        source_epoch = build.get("source_date_epoch")
        generated_at = build.get("generated_at")
        expected_generated_at = None
        if isinstance(source_epoch, int) and source_epoch >= release_provenance.ZIP_MINIMUM_EPOCH:
            expected_generated_at = datetime.fromtimestamp(source_epoch, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        checks.append(check("PASS" if isinstance(source_epoch, int) and source_epoch >= release_provenance.ZIP_MINIMUM_EPOCH else "FAIL", "release manifest source_date_epoch is valid"))
        checks.append(check("PASS" if generated_at == expected_generated_at else "FAIL", "release manifest generated_at matches source_date_epoch"))
        checks.append(check("PASS" if build.get("deterministic") is True else "FAIL", "release manifest declares deterministic build"))

        source = data.get("source") if isinstance(data.get("source"), dict) else {}
        checks.append(check("PASS" if source.get("vcs") == "git" else "FAIL", "release manifest source vcs is git"))
        checks.append(check("PASS" if isinstance(source.get("commit"), str) and release_provenance.HEX40_RE.fullmatch(source["commit"]) else "FAIL", "release manifest source commit is 40 lowercase hex"))
        checks.append(check("PASS" if isinstance(source.get("tree"), str) and release_provenance.HEX40_RE.fullmatch(source["tree"]) else "FAIL", "release manifest source tree is 40 lowercase hex"))
        checks.append(check("PASS" if source.get("dirty") is False else "FAIL", "release manifest source dirty is false"))

        archive_data = data.get("archive") if isinstance(data.get("archive"), dict) else {}
        checks.append(check("PASS" if archive_data.get("filename") == archive_path.name else "FAIL", "release manifest archive filename matches sidecar zip"))
        checks.append(check("PASS" if archive_data.get("format") == "zip" else "FAIL", "release manifest archive format is zip"))
        checks.append(check("PASS" if archive_data.get("size") == actual_size else "FAIL", "release manifest archive size matches zip bytes"))
        checks.append(check("PASS" if archive_data.get("sha256") == actual_sha else "FAIL", "release manifest archive sha256 matches zip bytes"))
        checks.append(check("PASS" if archive_data.get("entry_count") == len(infos) else "FAIL", "release manifest archive entry_count matches physical zip entries"))

        files = data.get("files")
        if not isinstance(files, list):
            checks.append(check("FAIL", "release manifest files is a list"))
            return checks
        manifest_names = [str(item.get("path")) for item in files if isinstance(item, dict) and item.get("path")]
        sorted_unique = manifest_names == sorted(manifest_names) and len(manifest_names) == len(set(manifest_names))
        checks.append(check("PASS" if sorted_unique else "FAIL", "release manifest files are sorted and unique by path"))
        checks.append(check("PASS" if len(files) == len(infos) else "FAIL", "release manifest files length matches physical zip entries"))

        physical_names = [info.filename for info in infos]
        unsafe: list[str] = []
        normalized_seen: set[str] = set()
        for info in infos:
            error = self.release_manifest_path_error(info.filename)
            normalized = unicodedata.normalize("NFC", info.filename).casefold()
            if normalized in normalized_seen:
                error = error or "archive path collides after Unicode/case normalization"
            normalized_seen.add(normalized)
            if info.flag_bits & 0x1:
                error = error or "encrypted archive member"
            mode = (info.external_attr >> 16) & 0o170000
            if mode and mode != 0o100000:
                error = error or "non-regular archive member"
            if error:
                unsafe.append(f"{info.filename}: {error}")
        checks.append(check("PASS" if not unsafe else "FAIL", "release archive physical members are safe regular files"))
        for item in unsafe[:20]:
            checks.append(check("FAIL", f"unsafe archive member: {item}"))

        checks.append(check("PASS" if sorted(physical_names) == manifest_names else "FAIL", "release manifest file list matches zip entries"))
        file_map = {str(item.get("path")): item for item in files if isinstance(item, dict) and item.get("path")}
        with zipfile.ZipFile(archive_path) as archive:
            mismatches: list[str] = []
            for info in infos:
                item = file_map.get(info.filename)
                if not isinstance(item, dict):
                    continue
                content = archive.read(info)
                if item.get("size") != len(content):
                    mismatches.append(f"{info.filename}: size")
                if item.get("sha256") != hashlib.sha256(content).hexdigest():
                    mismatches.append(f"{info.filename}: sha256")
                if not isinstance(item.get("sha256"), str) or not HEX64_RE.fullmatch(str(item.get("sha256"))):
                    mismatches.append(f"{info.filename}: sha256 format")
        checks.append(check("PASS" if not mismatches else "FAIL", "release manifest file size/hash entries match zip payloads"))
        for item in mismatches[:20]:
            checks.append(check("FAIL", f"release manifest file mismatch: {item}"))

        official_packs = data.get("official_packs")
        if isinstance(official_packs, list):
            ids = [str(item.get("id")) for item in official_packs if isinstance(item, dict)]
            valid = ids == sorted(ids) and len(ids) == len(set(ids))
            for item in official_packs:
                valid = valid and isinstance(item, dict)
                if isinstance(item, dict):
                    valid = valid and isinstance(item.get("id"), str) and bool(item.get("id"))
                    valid = valid and isinstance(item.get("version"), str) and bool(item.get("version"))
                    valid = valid and isinstance(item.get("manifest_path"), str) and bool(item.get("manifest_path"))
                    valid = valid and isinstance(item.get("manifest_sha256"), str) and bool(HEX64_RE.fullmatch(item["manifest_sha256"]))
            checks.append(check("PASS" if valid else "FAIL", "release manifest official_packs are sorted v1 provenance entries"))
        else:
            checks.append(check("FAIL", "release manifest official_packs is a list"))
        return checks
