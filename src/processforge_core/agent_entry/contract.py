"""Versioned startup contract and byte-preserving managed projections.

This module knows nothing about client discovery, Work grants or host enforcement.
Only reviewed, hash-declared text can be replaced as PF-owned content.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re


MAX_CONTRACT_BYTES = 4096
SOURCE_ROOT = Path(__file__).resolve().parents[3]
BOM = b"\xef\xbb\xbf"
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
BEGIN = re.compile(rb"(?m)^<!-- PF:ENTRY:BEGIN contract=([0-9]+\.[0-9]+\.[0-9]+) -->\r?\n")
END = re.compile(rb"(?m)^<!-- PF:ENTRY:END -->(?:\r?\n|$)")


class EntryError(ValueError):
    """Stable, content-free diagnostic suitable for public reports."""

    def __init__(self, reason: str, path: str = ""):
        super().__init__(reason)
        self.reason, self.path = reason, path


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def decode_json(raw: bytes, maximum: int = 65536):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise EntryError("duplicate_json_key")
            value[key] = item
        return value
    if len(raw) > maximum:
        raise EntryError("input_too_large")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(EntryError("invalid_json")))
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, EntryError):
            raise
        raise EntryError("invalid_json") from None


def text_bytes(raw: bytes) -> None:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError:
        raise EntryError("unsupported_encoding") from None
    if any(ord(char) < 32 and char not in "\n\r\t" for char in text):
        raise EntryError("binary_content")


@dataclass(frozen=True)
class Contract:
    version: str
    raw: bytes
    sha256: str
    source_digest: str
    known: tuple[tuple[str, str], ...]
    legacy: tuple[tuple[int, str, bytes], ...]
    extended: bytes

    def render(self, *, extended: bool = False) -> bytes:
        return self.raw + (b"\n" + self.extended if extended else b"")


def load_contract(root: Path = SOURCE_ROOT) -> Contract:
    templates = root / "templates"
    def read(name: str, maximum: int) -> bytes:
        with (templates / name).open("rb") as stream:
            value = stream.read(maximum + 1)
        if len(value) > maximum:
            raise EntryError("contract_source_invalid")
        return value
    try:
        raw = read("agent-entry-contract.md", MAX_CONTRACT_BYTES)
        meta_raw = read("agent-entry-contract.json", 65536)
        template = read("project-agents-template.md", 1048576)
    except OSError:
        raise EntryError("contract_source_unavailable") from None
    meta = decode_json(meta_raw)
    fields = {"schema_version", "contract_version", "sha256", "max_utf8_bytes", "known_blocks", "legacy_prefixes"}
    if (not isinstance(meta, dict) or set(meta) != fields or type(meta["schema_version"]) is not int
            or meta["schema_version"] != 1 or type(meta["max_utf8_bytes"]) is not int or meta["max_utf8_bytes"] != MAX_CONTRACT_BYTES
            or not isinstance(meta["contract_version"], str) or not VERSION.fullmatch(meta["contract_version"])):
        raise EntryError("contract_metadata_invalid")
    text_bytes(raw)
    version = meta["contract_version"]
    if (raw.startswith(BOM) or b"\r" in raw or len(raw) > MAX_CONTRACT_BYTES
            or not raw.startswith(f"<!-- PF:ENTRY:BEGIN contract={version} -->\n".encode())
            or not raw.endswith(b"<!-- PF:ENTRY:END -->\n") or raw.count(b"PF:ENTRY:") != 2
            or re.findall(rb"(?m)^([0-9]+)\. ", raw) != [str(i).encode() for i in range(1, 9)]):
        raise EntryError("contract_source_invalid")
    if meta["sha256"] != digest(raw):
        raise EntryError("contract_hash_mismatch")
    known = []
    if not isinstance(meta["known_blocks"], list) or not 1 <= len(meta["known_blocks"]) <= 64:
        raise EntryError("contract_metadata_invalid")
    for item in meta["known_blocks"]:
        if (not isinstance(item, dict) or set(item) != {"version", "sha256"}
                or not isinstance(item["version"], str) or not VERSION.fullmatch(item["version"])
                or not isinstance(item["sha256"], str) or not HASH.fullmatch(item["sha256"])):
            raise EntryError("contract_metadata_invalid")
        known.append((item["version"], item["sha256"]))
    if (version, digest(raw)) not in known or len({row[0] for row in known}) != len(known):
        raise EntryError("contract_metadata_invalid")
    legacy = []
    if not isinstance(meta["legacy_prefixes"], list) or len(meta["legacy_prefixes"]) > 32:
        raise EntryError("contract_metadata_invalid")
    for item in meta["legacy_prefixes"]:
        if (not isinstance(item, dict) or set(item) != {"lines", "sha256", "suffix_heading"}
                or type(item["lines"]) is not int or not 1 <= item["lines"] <= 256
                or not isinstance(item["sha256"], str) or not HASH.fullmatch(item["sha256"])
                or not isinstance(item["suffix_heading"], str)
                or not re.fullmatch(r"## [A-Za-z ]{1,64}", item["suffix_heading"])):
            raise EntryError("contract_metadata_invalid")
        legacy.append((item["lines"], item["sha256"], item["suffix_heading"].encode()))
    # The derivative carries L1 only after the exact K source. Drift is an error.
    if not template.startswith(raw + b"\n"):
        raise EntryError("derived_template_stale")
    extended = template[len(raw) + 1:]
    text_bytes(extended)
    if not extended or b"PF:ENTRY" in extended:
        raise EntryError("derived_template_invalid")
    return Contract(version, raw, digest(raw), digest(encoded([digest(raw), digest(meta_raw), digest(template)])),
                    tuple(known), tuple(legacy), extended)


def block_span(raw: bytes, contract: Contract) -> tuple[int, int] | None:
    text_bytes(raw)
    offset = len(BOM) if raw.startswith(BOM) else 0
    body = raw[offset:]
    if b"PF:ENTRY" not in body:
        return None
    begins, ends = list(BEGIN.finditer(body)), list(END.finditer(body))
    if len(begins) != 1 or len(ends) != 1 or body.count(b"PF:ENTRY") != 2 or begins[0].end() > ends[0].start():
        raise EntryError("managed_markers_invalid")
    start, end = offset + begins[0].start(), offset + ends[0].end()
    normalized = raw[start:end].replace(b"\r\n", b"\n")
    if not normalized.endswith(b"\n"):
        normalized += b"\n"
    version = begins[0].group(1).decode("ascii")
    if version not in {item[0] for item in contract.known}:
        raise EntryError("managed_version_unknown")
    if (version, digest(normalized)) not in contract.known:
        raise EntryError("managed_content_changed")
    if len(raw[start:end]) > MAX_CONTRACT_BYTES:
        raise EntryError("placed_contract_too_large")
    return start, end


def project_content(before: bytes | None, contract: Contract, *, hidden: bool) -> tuple[bytes, str]:
    if before is None:
        return contract.render(extended=hidden), "create"
    span = block_span(before, contract)
    if span:
        a, b = span
        # Leave even the line ending style of a current, valid projection intact.
        if before[a:b].replace(b"\r\n", b"\n").rstrip(b"\n") == contract.raw.rstrip(b"\n"):
            return before, "unchanged"
        return before[:a] + contract.raw + before[b:], "replace_block"
    if hidden:
        offset = len(BOM) if before.startswith(BOM) else 0
        body = before[offset:]
        for count, expected, heading in contract.legacy:
            prefix = b"".join(body.splitlines(keepends=True)[:count])
            suffix = body[len(prefix):]
            if (digest(prefix.replace(b"\r\n", b"\n")) == expected
                    and suffix.startswith((heading + b"\n", heading + b"\r\n"))):
                return before[:offset] + contract.raw + b"\n" + suffix, "migrate_legacy_prefix"
        raise EntryError("legacy_hidden_unknown")
    separator = b"" if not before or before.endswith(b"\n\n") else b"\n" if before.endswith(b"\n") else b"\n\n"
    return before + separator + contract.raw, "append_block"


def inspect_projection(raw: bytes | None, contract: Contract) -> dict:
    """Inspect actual bytes without preparing a replacement or requiring writes."""
    result = {"sha256": digest(raw) if raw is not None else None,
              "raw_bytes": len(raw) if raw is not None else 0,
              "k_start": None, "k_end": None, "k_raw_sha256": None,
              "k_normalized_sha256": None, "status": "blocked", "reason": "entry_file_missing"}
    if raw is None:
        return result
    try:
        span = block_span(raw, contract)
    except EntryError as exc:
        return dict(result, reason=exc.reason)
    if span is None:
        return dict(result, reason="entry_contract_missing")
    start, end = span
    block = raw[start:end]
    normalized = block.replace(b"\r\n", b"\n")
    if not normalized.endswith(b"\n"):
        normalized += b"\n"
    current = normalized == contract.raw
    return dict(result, k_start=start, k_end=end, k_raw_sha256=digest(block),
                k_normalized_sha256=digest(normalized), status="verified" if current else "blocked",
                reason="current_contract" if current else "entry_contract_outdated")
