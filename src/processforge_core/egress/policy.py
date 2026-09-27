"""Bounded whole-unit decisions; classification declarations are trusted inputs."""
from __future__ import annotations

import re
import time

from .contracts import EgressError, bounded_json, digest

# Fixed, reviewable expressions only; no operator/model supplied regex programs.
RULES = {
    "private_key": re.compile(r"-----BEGIN (?:[A-Z ]{0,32})PRIVATE KEY-----"),
    "synthetic_secret": re.compile(r"PF_SYNTHETIC_SECRET_[A-Za-z0-9_-]+"),
    "credential": re.compile(r"(?i)(?:\b(?:password|passwd|api[_-]?key|access[_-]?token|secret)\s*[\"']?\s*[:=]|\b(?:sk_live_|ghp_)[A-Za-z0-9]{8,}|\bBearer\s+[^\s\"']{8,})"),
    "personal_email": re.compile(r"[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,253}\.[A-Za-z]{2,24}"),
    "private_path": re.compile(r"(?i)(?:[a-z]:[/\\]|/(?:home|users|etc|var|tmp)/|\\\\[a-z0-9_.-]+\\)"),
    "raw_digest": re.compile(r"(?i)\b(?:sha256:)?[a-f0-9]{32,128}\b"),
    "opaque_encoding": re.compile(r"[A-Za-z0-9+/=_-]{80,}|(?i:\bbase64\s*[,=:])"),
}
STRONG = {"credential", "private_key", "synthetic_secret"}


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def decide(raw: bytes, declaration: dict, policy: dict, *, clock=time.monotonic, wall=time.time) -> dict:
    start = clock()
    limits = policy["limits"]
    if len(raw) > limits["unit_bytes"]:
        raise EgressError("content_budget_exceeded")
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        raise EgressError("unsupported_content") from None
    if any(ord(c) < 32 and c not in "\r\n\t" for c in text):
        raise EgressError("unsupported_content")
    scans = [text]
    if declaration["format"] == "json":
        value = bounded_json(raw, limits["unit_bytes"], limits["json_depth"])
        scans.extend(_strings(value))
    elif declaration["format"] != "text":
        raise EgressError("unsupported_content")
    findings = set()
    for name, expression in RULES.items():
        if any(expression.search(part) for part in scans if name != "personal_email" or "@" in part):
            findings.add(name)
        if (clock() - start) * 1000 > limits["classification_ms"]:
            raise EgressError("classification_timeout")
    source_digest = digest(raw)
    exceptions = [e for e in policy["exceptions"]
                  if e["checksum"] == source_digest and e["recipient"] == policy["recipient"]["id"]
                  and e["purpose"] == policy["recipient"]["purpose"] and wall() < e["expires"]
                  and e["detector"] in findings - STRONG]
    exempt = {e["detector"] for e in exceptions}
    not_after = min((e["expires"] for e in exceptions), default=None)
    findings -= exempt - STRONG
    label = declaration["classification"]
    if label == "unknown":
        raise EgressError("classification_unknown")
    if "opaque_encoding" in findings:
        raise EgressError("unsupported_content")
    effective = "credential" if findings & STRONG else ("restricted" if findings else label)
    if label in {"secret", "credential"}:
        effective = label
    if label == "public" and not findings:
        return {"decision": "allow", "text": text, "findings": [], "not_after": not_after}
    if declaration["required"]:
        raise EgressError("required_semantics_lost")
    transform = declaration["transform"]
    if transform == "none" or effective not in policy["redact_classes"]:
        raise EgressError("disclosure_denied")
    # An explicit whole-unit rule discards ALL original characters, including
    # filenames, keys, stdout, stderr, exceptions and attachment metadata.
    return {"decision": transform, "text": "[REDACTED]" if transform == "redact" else "",
            "findings": sorted(findings), "not_after": not_after}
