"""Reuse CJ1 for bounded new internal metadata, never for legacy raw import.

The existing 2 MiB/64 profile is selected explicitly for this kernel. It is not
an upgrade/public compatibility cap and does not reserialize historic objects.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from .compact_codec import canonical_bytes, decode_canonical
from .compact_model import CompactError, JsonValue, _freeze
from .mutation_model import MutationError

if TYPE_CHECKING:
    from .mutation_model import (
        Encoded,
        EntityFileUse,
        ImmutableLinkDraft,
        PreparedObject,
    )

CURRENT_FIELDS = frozenset(
    (
        "id",
        "run_id",
        "status",
        "objective",
        "created_at",
        "updated_at",
        "process",
        "context_id",
        "session",
    )
)


def encode(value: object) -> Encoded:
    """Copy caller JSON containers into immutable canonical bytes immediately."""
    from .mutation_model import Encoded

    try:
        return Encoded(canonical_bytes(_freeze(value)))
    except CompactError:
        raise MutationError("mutation_codec_invalid") from None


def validate_encoded(value: Encoded) -> None:
    """Strict version dispatch; unknown versions never trigger a repair."""
    if value.version != 1 or value.codec != "cj1":
        raise MutationError("mutation_codec_unsupported")
    try:
        decode_canonical(value.body)
    except CompactError:
        raise MutationError("mutation_codec_invalid") from None


def digest(value: Encoded) -> str:
    """Hash the actual frozen bytes, not a caller assertion."""
    return "sha256:" + hashlib.sha256(value.body).hexdigest()


def document(value: Encoded) -> Mapping[str, JsonValue]:
    """Decode only supported current metadata fields; reject hidden capabilities."""
    decoded = decode_canonical(value.body)
    if not isinstance(decoded, Mapping) or not set(decoded) <= CURRENT_FIELDS:
        raise MutationError("mutation_capability_unsupported")
    return decoded


def raw_text(value: JsonValue) -> str:
    """Preserve legacy truthy/string fallback for scalar current metadata."""
    if isinstance(value, (Mapping, tuple)):
        raise MutationError("mutation_metadata_unsupported")
    return str(value or "")


def target_path(value: str) -> str:
    """Portable project-relative link destination, with no filesystem reads."""
    from .mutation_model import text

    text(value, required=True)
    parts = value.split("/")
    devices = {"CON", "PRN", "AUX", "NUL"} | {
        f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(1, 10)
    }
    if (
        PurePosixPath(value).is_absolute()
        or any(
            not p
            or p in (".", "..")
            or any(c in p for c in '\\:*?"<>|')
            or any(ord(c) < 32 for c in p)
            or p.endswith((" ", "."))
            or p.split(".", 1)[0].upper() in devices
            for p in parts
        )
        or [p.casefold() for p in parts[:2]] == [".pf", "objects"]
    ):
        raise MutationError("mutation_target_invalid")
    return value


def use_descriptor(use: EntityFileUse) -> Encoded:
    """Closed v1 semantic history descriptor; never current lifecycle fields."""
    return encode(
        {
            "version": 1,
            "entity_kind": use.key.kind,
            "entity_id": use.key.entity_id,
            "revision": use.revision,
            "object_id": use.object_id,
            "role": use.role,
            "ordinal": use.ordinal,
            "codec": use.codec,
            "media_type": use.media_type,
            "logical_reference": use.logical_reference,
            "evidence_status": use.evidence_status,
        }
    )


def association_history(history: Encoded, uses: tuple[EntityFileUse, ...]) -> Encoded:
    """Wrap only changed history with exact ordered associations using CJ1."""
    if not uses:
        return history
    return encode(
        {
            "version": 1,
            "kind": "object_associations",
            "metadata": decode_canonical(history.body),
            "uses": tuple(decode_canonical(use_descriptor(u).body) for u in uses),
        }
    )


def link_payload(
    draft: ImmutableLinkDraft, obj: PreparedObject, operation_id: str
) -> Encoded:
    """Kernel-owned closed payload; caller cannot supply a conflicting hash."""
    return encode(
        {
            "version": 1,
            "kind": "immutable_link",
            "step_id": draft.step_id,
            "operation_id": operation_id,
            "project_id": obj.binding.project_id,
            "store_id": obj.binding.store_id,
            "generation": obj.binding.generation,
            "use": decode_canonical(use_descriptor(draft.use).body),
            "object_id": obj.object_id,
            "hash": "sha256:" + obj.ref.digest,
            "size": obj.ref.size,
            "ref_version": 1,
            "relative_path": obj.relative_path,
            "target": target_path(draft.target_key),
        }
    )
