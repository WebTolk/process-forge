"""Existing privacy findings and redaction policy for evolution content."""
from __future__ import annotations

import re
from typing import Any

from ..common.privacy import BACKSLASH, contains_secret_value, is_public_path_safe


class EvolvePrivacyPolicy:
    """Inspect and sanitize evolution values without retaining state."""

    def findings(self, text: str) -> list[str]:
        findings: list[str] = []
        if not is_public_path_safe(text):
            findings.append("private_absolute_path")
        if contains_secret_value(text):
            findings.append("secret_like_value")
        if re.search(r"(?im)^\s*[A-Za-z_][A-Za-z0-9_]*\s*=\s*[^\s#]+", text) and ".env" in text.lower():
            findings.append("env_value")
        if re.search(r"https?://[^\s/@]+:[^\s/@]+@", text):
            findings.append("credentialed_repo_url")
        if len(text) > 20000:
            findings.append("large_source_dump")
        return sorted(set(findings))

    def text(self, text: str) -> str:
        sanitized = text
        sanitized = re.sub(r"(?<![A-Za-z])[A-Za-z]:" + re.escape(BACKSLASH) + r"[^\n\r\t ]+", "<redacted-path>", sanitized)
        sanitized = re.sub(r"(?<![A-Za-z])[A-Za-z]:/[^\n\r\t ]+", "<redacted-path>", sanitized)
        sanitized = re.sub(r"/(?:home|Users|srv)/[^\n\r\t ]+", "<redacted-path>", sanitized)
        sanitized = re.sub(r"(?i)(api[_-]?key|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{8,}", r"\1: <redacted-secret>", sanitized)
        sanitized = re.sub(r"https?://([^\s/@]+):([^\s/@]+)@", "https://<redacted-credentials>@", sanitized)
        sanitized = re.sub(r"-----BEGIN [A-Z ]+PRIVATE KEY-----.*?-----END [A-Z ]+PRIVATE KEY-----", "<redacted-private-key>", sanitized, flags=re.DOTALL)
        return sanitized

    def value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self.value(child) for key, child in value.items()}
        if isinstance(value, list):
            return [self.value(item) for item in value]
        if isinstance(value, str):
            return self.text(value)
        return value
