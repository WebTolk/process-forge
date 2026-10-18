"""Trusted operator contracts. No model message is accepted as a policy."""
from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

LIMITS = {"unit_bytes": 1048576, "envelope_bytes": 4194304,
          "attempt_bytes": 33554432, "disclosures": 128, "json_depth": 16,
          "classification_ms": 2000, "token_seconds": 30}
CLASSES = {"public", "internal", "restricted", "personal", "secret", "credential", "unknown"}
DETECTORS = {"version": 1, "strong": ["credential", "private_key", "synthetic_secret"],
             "review": ["personal_email", "private_path", "opaque_encoding", "raw_digest"]}
PRIVATE_COMPONENT = ".pf-egress-private"
ID = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")
DIGEST = re.compile(r"sha256:[a-f0-9]{64}\Z")


class EgressError(ValueError):
    """Only stable codes cross an untrusted boundary; never echo exception text."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def encoded(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def fingerprint(value) -> str:
    return digest(encoded(value))


DETECTOR_DIGEST = fingerprint({"bundle": DETECTORS, "implementation": digest(Path(__file__).with_name("policy.py").read_bytes())})


def exact(value, required: set, optional: set | None = None):
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - (optional or set()):
        raise EgressError("egress_contract_invalid")


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise EgressError("egress_contract_invalid")
    return value


def checksum(value):
    if not isinstance(value, str) or not DIGEST.fullmatch(value):
        raise EgressError("egress_contract_invalid")
    return value


def relative(value):
    if (not isinstance(value, str) or not value or len(value) > 1024 or "\\" in value
            or value.startswith("/") or any(x in value for x in (":", "\x00", "*", "?", "["))
            or any(x.casefold() in {"", ".", "..", PRIVATE_COMPONENT} or x.endswith((".", " ")) for x in value.split("/"))):
        raise EgressError("source_scope_denied")
    return value


def bounded_json(raw: bytes, maximum: int, depth: int = 16):
    if len(raw) > maximum:
        raise EgressError("content_budget_exceeded")
    try:
        text = raw.decode("utf-8")
        # Bound nesting before the decoder allocates nested objects.
        level, quoted, escaped = 0, False, False
        for char in text:
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in "[{":
                level += 1
                if level > depth:
                    raise EgressError("content_budget_exceeded")
            elif char in "]}":
                level -= 1
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise EgressError("unsupported_content")
                result[key] = value
            return result
        def constant(_):
            raise EgressError("unsupported_content")
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, EgressError):
            raise
        raise EgressError("unsupported_content") from None


def validate_limits(value):
    exact(value, set(LIMITS))
    if any(type(value[k]) is not int or not 1 <= value[k] <= maximum for k, maximum in LIMITS.items()):
        raise EgressError("egress_contract_invalid")
    if not value["unit_bytes"] <= value["envelope_bytes"] <= value["attempt_bytes"]:
        raise EgressError("egress_contract_invalid")


def route(value):
    exact(value, {"id", "purpose", "endpoint", "transport"})
    identifier(value["id"])
    identifier(value["purpose"])
    if value["transport"] not in {"https-json-v1", "loopback-json-v1"}:
        raise EgressError("enforcement_unavailable")
    endpoint = value["endpoint"]
    if not isinstance(endpoint, str) or len(endpoint) > 2048 or any(ord(c) < 33 or ord(c) > 126 for c in endpoint):
        raise EgressError("recipient_invalid")
    try:
        url = urlsplit(endpoint)
        if not url.hostname or url.username or url.password or url.query or url.fragment or "%" in url.netloc:
            raise ValueError()
        port = url.port
        if port is not None and not 1 <= port <= 65535:
            raise ValueError()
        if value["transport"] == "loopback-json-v1":
            if url.scheme != "http" or not ipaddress.ip_address(url.hostname).is_loopback:
                raise ValueError()
        elif url.scheme != "https":
            raise ValueError()
    except ValueError:
        raise EgressError("recipient_invalid") from None
    return url


def validate_policy(value):
    exact(value, {"schema_version", "id", "recipient", "limits", "sources", "denied_sources",
                  "redact_classes", "exceptions", "tools"}, {"tool_bindings", "result"})
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise EgressError("egress_contract_invalid")
    identifier(value["id"])
    route(value["recipient"])
    validate_limits(value["limits"])
    sources = value["sources"]
    if not isinstance(sources, dict) or not 1 <= len(sources) <= 128:
        raise EgressError("egress_contract_invalid")
    for path, spec in sources.items():
        relative(path)
        exact(spec, {"classification", "checksum", "format", "required", "transform", "initial"})
        checksum(spec["checksum"])
        if (spec["classification"] not in CLASSES or spec["format"] not in {"text", "json"}
                or spec["transform"] not in {"none", "redact", "omit"}
                or type(spec["required"]) is not bool or type(spec["initial"]) is not bool):
            raise EgressError("egress_contract_invalid")
    for key in ("denied_sources", "redact_classes", "exceptions", "tools"):
        if not isinstance(value[key], list) or len(value[key]) > 128:
            raise EgressError("egress_contract_invalid")
    for path in value["denied_sources"]:
        relative(path)
    if any(x not in CLASSES - {"public", "unknown"} for x in value["redact_classes"]):
        raise EgressError("egress_contract_invalid")
    for name in value["tools"]:
        identifier(name)
    bindings = value.get("tool_bindings", {})
    if not isinstance(bindings, dict) or any(name not in value["tools"] for name in bindings):
        raise EgressError("egress_contract_invalid")
    for name, value_hash in bindings.items():
        identifier(name)
        checksum(value_hash)
    for exception in value["exceptions"]:
        exact(exception, {"checksum", "detector", "recipient", "purpose", "expires"})
        checksum(exception["checksum"])
        if exception["detector"] not in DETECTORS["review"]:
            raise EgressError("exception_forbidden")
        identifier(exception["recipient"])
        identifier(exception["purpose"])
        if type(exception["expires"]) is not int or exception["expires"] < 1:
            raise EgressError("egress_contract_invalid")
    if "result" in value:
        result = value["result"]
        exact(result, {"classification", "required", "transform", "format"})
        if (result["classification"] not in CLASSES or result["format"] != "text"
                or type(result["required"]) is not bool or result["transform"] not in {"none", "redact", "omit"}):
            raise EgressError("egress_contract_invalid")
    return copy.deepcopy(value)


def binding_for(policy):
    policy = validate_policy(policy)
    return {"policy_id": policy["id"], "policy_checksum": fingerprint(policy),
            "detector_checksum": DETECTOR_DIGEST, "recipient": policy["recipient"]["id"],
            "purpose": policy["recipient"]["purpose"], "minimum_enforcement": "mediated_session",
            "limits": copy.deepcopy(policy["limits"])}


def validate_binding(value):
    exact(value, {"policy_id", "policy_checksum", "detector_checksum", "recipient", "purpose", "minimum_enforcement", "limits"})
    for name in ("policy_id", "recipient", "purpose"):
        identifier(value[name])
    checksum(value["policy_checksum"])
    checksum(value["detector_checksum"])
    if value["minimum_enforcement"] != "mediated_session":
        raise EgressError("enforcement_unavailable")
    validate_limits(value["limits"])
    return copy.deepcopy(value)


def security_intent(value):
    exact(value, {"egress", "allowed_read_files"}, {"predecessor"})
    result = {"egress": validate_binding(value["egress"])}
    paths = value["allowed_read_files"]
    if not isinstance(paths, list) or len(paths) > 128:
        raise EgressError("egress_contract_invalid")
    result["allowed_read_files"] = sorted(set(relative(p) for p in paths))
    if "predecessor" in value:
        exact(value["predecessor"], {"assignment_id", "capsule_checksum"})
        # Work slugs can exceed policy identifier length.
        name = value["predecessor"]["assignment_id"]
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,159}", name):
            raise EgressError("egress_contract_invalid")
        checksum(value["predecessor"]["capsule_checksum"])
        result["predecessor"] = copy.deepcopy(value["predecessor"])
    return result


def require_v2(contract):
    if not isinstance(contract, dict) or contract.get("contract_version") != 2:
        raise EgressError("egress_contract_required")
    binding = validate_binding(contract.get("egress"))
    if contract.get("assignment_intent", {}).get("egress") != binding:
        raise EgressError("invalid_binding")
    return binding
