from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from processforge_core.common.paths import rel


UPDATE_SOURCE_PUBLIC_KEYS = [
    "id",
    "type",
    "provider",
    "priority",
    "manifest_url",
    "changelog_url",
    "channel",
    "path",
    "owner",
    "repo",
    "api_base_url",
    "channels",
    "include_prereleases",
    "asset_patterns",
    "trust",
    "policy",
    "provider_capabilities",
]


UPDATE_SOURCE_LOCAL_KEYS = [
    "auth_ref",
    "auth",
    "headers_env",
    "query_env",
    "custom_headers_env",
    "channel_override",
]


class UpdateSitePolicy:
    def location(self, source: dict[str, Any], provider_key: str) -> str:
        return str(source.get("manifest_url") or "")

    def source_kind(self, source: dict[str, Any]) -> str:
        manifest_url = self.location(source, "provider")
        parsed = urlparse(manifest_url)
        scheme = parsed.scheme.lower()
        if scheme == "file" or not scheme:
            return "local_file"
        if scheme in {"http", "https"}:
            return "http"
        return scheme or "unknown"

    def source_id(self, source: dict[str, Any]) -> str:
        raw = source.get("id")
        if isinstance(raw, str) and raw.strip():
            return raw
        manifest_url = self.location(source, "provider")
        digest = hashlib.sha256(manifest_url.encode("utf-8")).hexdigest()[:12] if manifest_url else "missing"
        return f"manifest-{digest}"

    def stable_key(self, subject_type: str, subject_id: str, source_id: str) -> str:
        return f"{subject_type}:{subject_id}:{source_id}"

    def record(
        self,
        workplace_root: Path,
        subject_type: str,
        subject_id: str,
        subject_scope: str,
        installed_version: str,
        manifest_path: Path,
        site: dict[str, Any],
        overrides: dict[str, dict[str, Any]],
        *,
        parent: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        source_id = self.source_id(site)
        site_id = self.stable_key(subject_type, subject_id, source_id)
        source = {key: site[key] for key in UPDATE_SOURCE_PUBLIC_KEYS if key in site}
        source["id"] = source_id
        source["type"] = self.source_kind(source)
        if "channel" not in source:
            channels = site.get("channels")
            if isinstance(channels, list) and channels:
                source["channel"] = str(channels[0])
        enabled = bool(site.get("enabled", True))
        preserved = {key: site[key] for key in UPDATE_SOURCE_LOCAL_KEYS if key in site}
        override = overrides.get(site_id, {}) or overrides.get(subject_id, {}) or overrides.get(f"{subject_type}:{subject_id}", {})
        if isinstance(override, dict):
            if "enabled" in override or "disabled" in override:
                enabled = bool(override.get("enabled", not bool(override.get("disabled"))))
            if isinstance(override.get("channels"), list):
                source["channels"] = override.get("channels")
            if isinstance(override.get("channel"), str):
                source["channel"] = override.get("channel")
                source["channels"] = [override.get("channel")]
            if isinstance(override.get("manifest_url"), str):
                source["manifest_url"] = override.get("manifest_url")
            if not isinstance(source.get("policy"), dict):
                source["policy"] = {}
            if isinstance(override.get("pin_version"), str):
                source["policy"]["pin_version"] = override.get("pin_version")
            if "allow_major" in override:
                source["policy"]["allow_major"] = bool(override.get("allow_major"))
            if "auto_apply" in override:
                source["policy"]["auto_apply"] = bool(override.get("auto_apply"))
            preserved_override = override.get("preserved_local") if isinstance(override.get("preserved_local"), dict) else {}
            for key in UPDATE_SOURCE_LOCAL_KEYS:
                if key in override:
                    preserved[key] = override[key]
            preserved.update(preserved_override)

        subject: dict[str, Any] = {"type": subject_type, "id": subject_id, "scope": subject_scope}
        if installed_version:
            subject["installed_version"] = installed_version
        if parent:
            subject["parent"] = parent
        record: dict[str, Any] = {
            "site_id": site_id,
            "subject": subject,
            "source": source,
            "manifest_path": rel(manifest_path, workplace_root),
            "enabled": enabled,
        }
        if preserved:
            record["preserved_local"] = preserved
        return record

    def policy(self, source: dict[str, Any], installed_subject: dict[str, Any] | None = None) -> dict[str, Any]:
        policy: dict[str, Any] = {}
        if isinstance(source.get("policy"), dict):
            policy.update(source["policy"])
        if installed_subject and isinstance(installed_subject.get("update_policy"), dict):
            policy.update(installed_subject["update_policy"])
        return policy
