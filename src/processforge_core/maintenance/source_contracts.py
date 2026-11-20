from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from processforge_core.common.checks import Check, check


UPDATE_SUBJECT_TYPES = {
    "*",
    "processforge_distribution",
    "workplace",
    "process_package",
    "knowledge_package",
    "template_package",
    "tool_package",
    "tool_definition",
    "mcp_definition",
    "knowledge_resource",
    "process_definition",
    "reusable_template",
    "platform_contract",
    "project_pf",
    # Legacy aliases kept for existing registries and smokes.
    "template",
    "tool",
    "mcp_server",
    "package",
}
CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
ENV_REFERENCE_RE = re.compile(r"^(?:[A-Z_][A-Z0-9_]*|\$\{[A-Z_][A-Z0-9_]*\}|(?:auth_ref|secret_ref):[A-Za-z0-9][A-Za-z0-9_.-]*)$")


class UpdateSourceContractPolicy:
    """Validate update source contracts and preserve registry source ordering."""

    def requires_https(self, source: dict[str, Any], defaults: dict[str, Any] | None = None) -> bool:
        trust = source.get("trust") if isinstance(source.get("trust"), dict) else {}
        if "require_https" in trust:
            return bool(trust.get("require_https"))
        if defaults and "require_https" in defaults:
            return bool(defaults.get("require_https"))
        return True

    def remote_url_shape(self, url: str, *, require_https: bool) -> tuple[bool, str]:
        if CONTROL_CHAR_RE.search(url) or any(char.isspace() for char in url):
            return False, "must not contain whitespace or control characters"
        parsed = urlparse(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            return False, "must be a valid remote URL with scheme and host"
        if require_https and parsed.scheme.lower() != "https":
            return False, "must use https unless local trust policy disables require_https"
        return True, ""

    def artifact_url_shape(self, url: str, artifact: dict[str, Any]) -> tuple[bool, str]:
        if CONTROL_CHAR_RE.search(url) or any(char.isspace() for char in url):
            return False, "must not contain whitespace or control characters"
        parsed = urlparse(url)
        if parsed.scheme.lower() == "file":
            if parsed.path or parsed.netloc:
                return True, ""
            return False, "file URL must include a path"
        if parsed.scheme.lower() in {"http", "https"}:
            if not parsed.netloc:
                return False, "remote URL must include a host"
            if self.requires_https(artifact) and parsed.scheme.lower() != "https":
                return False, "remote URL must use https unless local trust policy disables require_https"
            return True, ""
        return False, "must be an https or file URL"

    def append_env_checks(self, checks: list[Check], source: dict[str, Any], label: str) -> None:
        for field in ("headers_env", "query_env", "custom_headers_env"):
            values = source.get(field)
            if values is None:
                continue
            if not isinstance(values, dict):
                checks.append(check("FAIL", f"{label} {field} must be an object"))
                continue
            for key, value in values.items():
                if not isinstance(value, str) or not ENV_REFERENCE_RE.fullmatch(value):
                    checks.append(check("FAIL", f"{label} {field}.{key} must be an env variable name or auth_ref:/secret_ref: reference"))

    def append_source_checks(
        self,
        checks: list[Check],
        source: Any,
        label: str,
        *,
        provider_key: str,
        defaults: dict[str, Any] | None = None,
        require_subjects: bool = False,
        require_priority: bool = False,
    ) -> None:
        if not isinstance(source, dict):
            checks.append(check("FAIL", f"{label} must be an object"))
            return

        source_id = source.get("id")
        if source_id is not None and (not isinstance(source_id, str) or not source_id.strip()):
            checks.append(check("FAIL", f"{label} id must be a non-empty string when present"))
        elif isinstance(source_id, str) and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", source_id):
            checks.append(check("FAIL", f"{label} id must use letters, digits, dot, underscore, or hyphen"))

        enabled = source.get("enabled")
        if enabled is not None and not isinstance(enabled, bool):
            checks.append(check("FAIL", f"{label} enabled must be a boolean when present"))

        provider = source.get(provider_key)
        if not provider:
            provider = source.get("provider" if provider_key == "type" else "type")
        if provider is not None and (not isinstance(provider, str) or not provider.strip()):
            checks.append(check("FAIL", f"{label} {provider_key} must be a non-empty string when present"))

        if "url" in source:
            checks.append(check("FAIL", f"{label} uses unsupported url field; use manifest_url"))

        if "priority" not in source:
            if require_priority:
                checks.append(check("FAIL", f"{label} missing priority"))
        elif not isinstance(source.get("priority"), int):
            checks.append(check("FAIL", f"{label} priority must be an integer"))

        channels = source.get("channels")
        if channels is not None and (
            not isinstance(channels, list) or not all(isinstance(item, str) and item.strip() for item in channels)
        ):
            checks.append(check("FAIL", f"{label} channels must be a list of non-empty strings"))

        if require_subjects:
            subjects = source.get("subjects")
            if not isinstance(subjects, list) or not subjects:
                checks.append(check("FAIL", f"{label} missing subjects"))
            else:
                for index, subject in enumerate(subjects):
                    subject_label = f"{label}.subjects[{index}]"
                    if not isinstance(subject, dict):
                        checks.append(check("FAIL", f"{subject_label} must be an object"))
                        continue
                    subject_type = subject.get("type")
                    ids = subject.get("ids")
                    if subject_type not in UPDATE_SUBJECT_TYPES:
                        checks.append(check("FAIL", f"{subject_label}.type unsupported subject type {subject_type!r}"))
                    if not isinstance(ids, list) or not all(isinstance(item, str) and item.strip() for item in ids):
                        checks.append(check("FAIL", f"{subject_label}.ids must be a list of non-empty strings"))

        manifest_url = source.get("manifest_url")
        if not isinstance(manifest_url, str) or not manifest_url.strip():
            checks.append(check("FAIL", f"{label} missing manifest_url"))
        else:
            parsed = urlparse(manifest_url)
            scheme = parsed.scheme.lower()
            if scheme in {"http", "https"}:
                valid, reason = self.remote_url_shape(manifest_url, require_https=self.requires_https(source, defaults))
                if not valid:
                    checks.append(check("FAIL", f"{label} manifest_url {reason}"))
            elif scheme == "file" or not scheme:
                if CONTROL_CHAR_RE.search(manifest_url) or any(char.isspace() for char in manifest_url):
                    checks.append(check("FAIL", f"{label} manifest_url must not contain whitespace or control characters"))
                if scheme == "file" and not (parsed.path or parsed.netloc):
                    checks.append(check("FAIL", f"{label} manifest_url file URL must include a path"))
            else:
                checks.append(check("FAIL", f"{label} manifest_url unsupported scheme {scheme!r}"))

        changelog_url = source.get("changelog_url")
        if not isinstance(changelog_url, str) or not changelog_url.strip():
            checks.append(check("FAIL", f"{label} missing changelog_url"))

        auth = source.get("auth")
        if isinstance(auth, dict):
            for key in auth:
                if str(key).lower() in {"token", "password", "secret", "authorization", "api_key"}:
                    checks.append(check("FAIL", f"{label} auth must not contain raw secret key {key!r}; use *_env or auth_ref"))
        self.append_env_checks(checks, source, label)

    def validate_registry(self, data: dict[str, Any], path: Path) -> list[Check]:
        checks: list[Check] = []
        if not data:
            return [check("FAIL", f"{path} missing or invalid")]
        if data.get("schema_version") != 1:
            checks.append(check("FAIL", "update source registry schema_version must be 1"))
        if data.get("product") != "processforge":
            checks.append(check("FAIL", "update source registry product must be processforge"))
        defaults = data.get("defaults") if isinstance(data.get("defaults"), dict) else {}
        sources = data.get("sources")
        if not isinstance(sources, list):
            checks.append(check("FAIL", "update source registry sources must be a list"))
            return checks

        seen: set[str] = set()
        for index, source in enumerate(sources):
            source_id = source.get("id") if isinstance(source, dict) else None
            if isinstance(source_id, str):
                if source_id in seen:
                    checks.append(check("FAIL", f"sources[{index}] duplicate id {source_id}"))
                seen.add(source_id)
            self.append_source_checks(
                checks,
                source,
                f"sources[{index}]",
                provider_key="provider",
                defaults=defaults,
                require_subjects=False,
                require_priority=False,
            )
        if not checks:
            checks.append(check("PASS", f"{path} valid"))
        return checks

    def sorted_sources(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        sources = data.get("sources") if isinstance(data.get("sources"), list) else []
        indexed = [(index, source) for index, source in enumerate(sources) if isinstance(source, dict)]
        indexed.sort(key=lambda item: (not bool(item[1].get("enabled")), int(item[1].get("priority", 1000)), item[0]))
        return [source for _, source in indexed]
