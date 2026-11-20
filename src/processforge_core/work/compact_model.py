"""Immutable internal values for the disconnected compact capsule slice."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, TypeAlias, Union
from uuid import UUID

JsonValue: TypeAlias = Union[
    None, bool, int, str, tuple["JsonValue", ...], Mapping[str, "JsonValue"]
]

MAX_BYTES = 2 * 1024 * 1024
MAX_NESTING = 64
INT_MIN = -(2**63)
INT_MAX = 2**63 - 1


class CompactError(ValueError):
    """Expose a stable internal code without paths or untrusted contents."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _string(value: object) -> str:
    if type(value) is not str:
        raise CompactError("invalid_string")
    if len(value) > MAX_BYTES:
        raise CompactError("size_limit")
    if any(char == "\x00" or 0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise CompactError("invalid_string")
    return value


def _freeze(value: object) -> JsonValue:
    """Copy containers, validating depth and a conservative allocation bound."""
    remaining = MAX_BYTES

    def visit(item: object, depth: int) -> JsonValue:
        nonlocal remaining
        remaining -= 1
        if remaining < 0:
            raise CompactError("size_limit")
        if item is None or type(item) is bool:
            return item
        if type(item) is int:
            if not INT_MIN <= item <= INT_MAX:
                raise CompactError("integer_overflow")
            return item
        if type(item) is str:
            result = _string(item)
            remaining -= len(result)
            if remaining < 0:
                raise CompactError("size_limit")
            return result
        if depth >= MAX_NESTING:
            raise CompactError("nesting_limit")
        if isinstance(item, Mapping):
            result_map: dict[str, JsonValue] = {}
            for key, child in item.items():
                key = _string(key)
                remaining -= len(key) + 1
                if remaining < 0:
                    raise CompactError("size_limit")
                result_map[key] = visit(child, depth + 1)
            return MappingProxyType(result_map)
        if isinstance(item, (tuple, list)) and type(item) in (tuple, list):
            return tuple(visit(child, depth + 1) for child in item)
        raise CompactError("unsupported_value")

    return visit(value, 0)


@dataclass(frozen=True)
class ObjectRef:
    """An exact byte reference, never an authorization capability."""

    algorithm: Literal["sha256"]
    digest: str
    size: int
    media_type: str
    codec: str

    def __post_init__(self) -> None:
        if type(self.algorithm) is not str or self.algorithm != "sha256":
            raise CompactError("unsupported_algorithm")
        if not re.fullmatch(r"[a-f0-9]{64}", _string(self.digest)):
            raise CompactError("invalid_digest")
        if type(self.size) is not int or not 0 <= self.size <= INT_MAX:
            raise CompactError("invalid_size")
        if not _string(self.media_type) or not _string(self.codec):
            raise CompactError("invalid_reference")


@dataclass(frozen=True)
class CapsuleIdentity:
    """A project binding and exact logical Work selectors."""

    project_uuid: str
    project_id: str
    run_id: str
    assignment_id: str
    context_id: str

    def __post_init__(self) -> None:
        try:
            parsed = UUID(_string(self.project_uuid))
        except (ValueError, AttributeError):
            raise CompactError("invalid_identity") from None
        if str(parsed) != self.project_uuid:
            raise CompactError("invalid_identity")
        for value in (
            self.project_id,
            self.run_id,
            self.assignment_id,
            self.context_id,
        ):
            if not re.fullmatch(r"[a-z0-9]+(?:-+[a-z0-9]+)*", _string(value)):
                raise CompactError("invalid_identity")


@dataclass(frozen=True)
class CompactPlan:
    """Canonical envelope and deduplicated small objects, ordered by digest."""

    envelope_bytes: bytes
    envelope_checksum: str
    objects: tuple[tuple[ObjectRef, bytes], ...]

    def __post_init__(self) -> None:
        if type(self.envelope_bytes) is not bytes:
            raise CompactError("invalid_bytes")
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", _string(self.envelope_checksum)):
            raise CompactError("invalid_checksum")
        objects = tuple((ref, raw) for ref, raw in self.objects)
        if any(
            type(ref) is not ObjectRef or type(raw) is not bytes for ref, raw in objects
        ):
            raise CompactError("invalid_object")
        digests = tuple(ref.digest for ref, _ in objects)
        if digests != tuple(sorted(set(digests))):
            raise CompactError("invalid_object_order")
        object.__setattr__(self, "objects", objects)


@dataclass(frozen=True)
class VerifiedCapsule:
    """Verified storage, not execution readiness or a current permission grant."""

    storage_version: int
    identity: CapsuleIdentity
    raw_checksum: str
    document: Mapping[str, JsonValue]
    material: tuple[Mapping[str, JsonValue], ...]

    def __post_init__(self) -> None:
        if type(self.storage_version) is not int or self.storage_version != 2:
            raise CompactError("unsupported_storage")
        if type(self.identity) is not CapsuleIdentity:
            raise CompactError("invalid_identity")
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", _string(self.raw_checksum)):
            raise CompactError("invalid_checksum")
        document = _freeze(self.document)
        material = _freeze(self.material)
        if not isinstance(document, Mapping) or not isinstance(material, tuple):
            raise CompactError("invalid_document")
        if any(not isinstance(item, Mapping) for item in material):
            raise CompactError("invalid_material")
        object.__setattr__(self, "document", document)
        object.__setattr__(self, "material", material)
