"""Pure update manifest normalization and version selection rules."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from processforge_core.common.ids import safe_id
from processforge_core.maintenance.sites import UpdateSitePolicy
from processforge_core.resources.versioning import ResourceVersionPolicy

_UpdateVersionKey = tuple[
    int, tuple[int, ...], bool, tuple[tuple[int, int | str], ...], str
]


class UpdateVersionSelectionPolicy:
    """Select existing update records without fetching or applying updates."""

    def __init__(self) -> None:
        self._resource_version_policy = ResourceVersionPolicy()
        self._update_site_policy = UpdateSitePolicy()

    def latest(
        self, update_index: dict[str, Any], channel: str
    ) -> dict[str, Any] | None:
        channels = (
            update_index.get("channels", {})
            if isinstance(update_index.get("channels"), dict)
            else {}
        )
        latest = None
        channel_data = channels.get(channel)
        if isinstance(channel_data, dict):
            latest = channel_data.get("latest")
        elif isinstance(channel_data, str):
            latest = channel_data
        versions = (
            update_index.get("versions")
            if isinstance(update_index.get("versions"), list)
            else []
        )
        for item in versions:
            if isinstance(item, dict) and str(item.get("version")) == str(latest):
                return item
        return None

    def normalize(
        self, raw: dict[str, Any], site: dict[str, Any], channel: str
    ) -> list[dict[str, Any]]:
        subject = site.get("subject") if isinstance(site.get("subject"), dict) else {}
        manifest_subject = (
            raw.get("subject") if isinstance(raw.get("subject"), dict) else {}
        )
        subject_type = str(manifest_subject.get("type") or subject.get("type") or "")
        subject_id = str(manifest_subject.get("id") or subject.get("id") or "")
        source = site.get("source") if isinstance(site.get("source"), dict) else site
        source_id = str(source.get("id") or site.get("site_id") or "update-site")
        manifest_url = self._update_site_policy.location(source, "provider")
        site_changelog = str(source.get("changelog_url") or "")
        versions: list[dict[str, Any]] = []

        channels = raw.get("channels") if isinstance(raw.get("channels"), dict) else {}
        channel_data = channels.get(channel)
        if isinstance(channel_data, dict):
            for item in (
                channel_data.get("versions", [])
                if isinstance(channel_data.get("versions"), list)
                else []
            ):
                if not isinstance(item, dict):
                    continue
                versions.append(
                    {
                        "subject": {
                            "type": subject_type,
                            "id": subject_id,
                            "scope": str(subject.get("scope") or "global"),
                        },
                        "version": str(item.get("version") or ""),
                        "source_id": source_id,
                        "manifest_url": manifest_url,
                        "changelog_url": str(
                            item.get("changelog_url") or site_changelog
                        ),
                        "download_url": str(
                            item.get("download_url") or item.get("url") or ""
                        ),
                        "sha256": str(item.get("sha256") or ""),
                        "size_bytes": item.get("size_bytes") or item.get("size"),
                        "breaking": bool(item.get("breaking", False)),
                        "migration_required": bool(
                            item.get("migration_required", False)
                        ),
                        "notes": item.get("notes"),
                        "post_update_doctor": item.get("post_update_doctor")
                        if isinstance(item.get("post_update_doctor"), list)
                        else [],
                        "update_policy": item.get("update_policy")
                        if isinstance(item.get("update_policy"), dict)
                        else {},
                    }
                )

        for manifest_subject_item in (
            raw.get("subjects", []) if isinstance(raw.get("subjects"), list) else []
        ):
            if not isinstance(manifest_subject_item, dict):
                continue
            normalized_subject = {
                "type": str(manifest_subject_item.get("type") or subject_type),
                "id": str(manifest_subject_item.get("id") or subject_id),
                "scope": str(
                    subject.get("scope")
                    or manifest_subject_item.get("scope")
                    or "global"
                ),
            }
            if (
                normalized_subject["id"]
                and subject_id
                and normalized_subject["id"] != subject_id
            ):
                continue
            for item in (
                manifest_subject_item.get("versions", [])
                if isinstance(manifest_subject_item.get("versions"), list)
                else []
            ):
                if not isinstance(item, dict):
                    continue
                item_channels = item.get("channels")
                if isinstance(item_channels, list) and channel not in item_channels:
                    continue
                artifacts = (
                    item.get("artifacts")
                    if isinstance(item.get("artifacts"), list)
                    else []
                )
                artifact = next(
                    (entry for entry in artifacts if isinstance(entry, dict)), {}
                )
                migration = (
                    item.get("migration")
                    if isinstance(item.get("migration"), dict)
                    else {}
                )
                release = (
                    item.get("release") if isinstance(item.get("release"), dict) else {}
                )
                versions.append(
                    {
                        "subject": normalized_subject,
                        "version": str(item.get("version") or ""),
                        "source_id": source_id,
                        "manifest_url": manifest_url,
                        "changelog_url": str(
                            item.get("changelog_url")
                            or release.get("changelog_url")
                            or site_changelog
                        ),
                        "download_url": str(artifact.get("url") or ""),
                        "sha256": str(artifact.get("sha256") or ""),
                        "size_bytes": artifact.get("size")
                        or artifact.get("size_bytes"),
                        "breaking": any(
                            bool(change.get("breaking"))
                            for change in item.get("changes", [])
                            if isinstance(change, dict)
                        ),
                        "migration_required": bool(migration.get("required", False)),
                        "notes": item.get("notes"),
                        "post_update_doctor": item.get("post_update_doctor")
                        if isinstance(item.get("post_update_doctor"), list)
                        else [],
                        "update_policy": item.get("update_policy")
                        if isinstance(item.get("update_policy"), dict)
                        else {},
                    }
                )
        return [item for item in versions if item.get("version")]

    def _version_key(self, value: str) -> _UpdateVersionKey:
        """Order update releases while retaining legacy resource version parsing."""
        text = value.strip()
        match = re.fullmatch(
            r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?"
            r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
            r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?",
            text,
        )
        if match is None:
            legacy = self._resource_version_policy.key(value)[1]
            if isinstance(legacy, tuple):
                return (0, legacy, True, (), "")
            return (1, (), True, (), legacy)
        numeric = tuple(int(part or "0") for part in match.groups()[:3])
        prerelease = match.group(4)
        identifiers: tuple[tuple[int, int | str], ...] = (
            tuple(
                (0, int(part)) if part.isdecimal() else (1, part)
                for part in prerelease.split(".")
            )
            if prerelease
            else ()
        )
        return (0, numeric, prerelease is None, identifiers, "")

    def select(
        self, versions: list[dict[str, Any]], installed: str | None
    ) -> tuple[dict[str, Any] | None, list[str]]:
        warnings: list[str] = []
        newer: list[dict[str, Any]] = []
        installed_key = self._version_key(installed) if installed else None
        for item in versions:
            available = str(item.get("version") or "")
            available_key = self._version_key(available)
            if (
                installed_key is not None
                and not available_key[0]
                and not installed_key[0]
            ):
                is_newer, warning = available_key > installed_key, None
            else:
                is_newer, warning = self._resource_version_policy.is_newer(
                    available, installed
                )
            if warning:
                warnings.append(warning)
            if is_newer:
                newer.append(item)
        if not newer:
            return None, warnings
        newer.sort(key=lambda item: self._version_key(str(item.get("version") or "")))
        return newer[-1], sorted(set(warnings))

    def candidate_id(
        self, subject_type: str, subject_id: str, available_version: str, source_id: str
    ) -> str:
        raw = f"{subject_type}:{subject_id}:{available_version}:{source_id}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
        return f"candidate-{safe_id(subject_type)}-{safe_id(subject_id)}-{safe_id(available_version)}-{digest}"
