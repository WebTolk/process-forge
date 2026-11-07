"""Closed immutable inputs for the trusted, disconnected metadata writer.

These values convey neither domain approval nor host/file authority. Metadata
and immutable association variants are closed; binding/reservation operations
remain absent. A caller cannot pass SQL or callbacks across this boundary.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, fields, is_dataclass
from types import UnionType
from typing import Literal, get_args, get_origin, get_type_hints

from .compact_model import ObjectRef
from .compact_objects import ProjectObjectStore, object_relative_path

INT64_MAX = 2**63 - 1


class MutationError(ValueError):
    """Stable internal refusal with an exact recovery selector when necessary."""

    def __init__(self, code: str, operation_id: str = "") -> None:
        self.code = code
        self.operation_id = operation_id
        super().__init__(code)


def text(value: object, *, required: bool = False) -> str:
    """Validate text without trimming keys, normalizing or coercing values."""
    if (
        type(value) is not str
        or "\x00" in value
        or any(0xD800 <= ord(c) <= 0xDFFF for c in value)
        or (required and not value)
    ):
        raise MutationError("mutation_input_invalid")
    return value


def integer(value: object, minimum: int = 0) -> int:
    """Require exact int64; bool and floating point are not integers here."""
    if type(value) is not int or not minimum <= value <= INT64_MAX:
        raise MutationError("mutation_integer_invalid")
    return value


def _matches(value: object, annotation: object) -> bool:
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is UnionType:
        return any(_matches(value, child) for child in args)
    if origin is Literal:
        return any(type(value) is type(child) and value == child for child in args)
    if origin is tuple:
        return type(value) is tuple and all(_matches(v, args[0]) for v in value)
    return type(value) is annotation


class _Value:
    __slots__ = ()

    def __post_init__(self) -> None:
        if not is_dataclass(self):
            raise MutationError("mutation_input_invalid")
        hints = get_type_hints(type(self))
        for field in fields(self):
            value = getattr(self, field.name)
            if not _matches(value, hints[field.name]):
                raise MutationError("mutation_input_invalid")
            if type(value) is str:
                text(value)
            elif type(value) is int:
                integer(value, -1 if field.name == "ordinal" else 0)


@dataclass(frozen=True, slots=True)
class Encoded(_Value):
    """Exact canonical bytes; validated by the existing CJ1 primitives."""

    body: bytes
    version: int = 1
    codec: Literal["cj1"] = "cj1"

    def __post_init__(self) -> None:
        _Value.__post_init__(self)
        from .mutation_codec import validate_encoded

        validate_encoded(self)


@dataclass(frozen=True, slots=True)
class StoreBinding(_Value):
    """Physical Database identity and canonical Work generation, not a grant."""

    project_id: str
    store_id: str
    owner_id: str
    generation: int


@dataclass(frozen=True, slots=True)
class EntityKey(_Value):
    """Current entity identity; this slice supports Run and Assignment only."""

    kind: Literal["run", "assignment"]
    entity_id: str

    def __post_init__(self) -> None:
        _Value.__post_init__(self)
        text(self.entity_id, required=True)


@dataclass(frozen=True, slots=True)
class ExpectedEntity(_Value):
    """None means mandatory absence; never a wildcard."""

    key: EntityKey
    revision: int | None

    def __post_init__(self) -> None:
        _Value.__post_init__(self)
        if self.revision is not None:
            integer(self.revision, 1)


@dataclass(frozen=True, slots=True)
class ReadProof(_Value):
    """Complete entity read set and catalog CAS against phantom changes."""

    catalog_revision: int
    entities: tuple[ExpectedEntity, ...]


@dataclass(frozen=True, slots=True)
class EntityAfter(_Value):
    """Bounded current metadata; history and members live in separate rows."""

    key: EntityKey
    payload: Encoded
    source_order: str = ""
    integrity: Literal["valid", "placeholder", "orphan", "invalid"] = "valid"


@dataclass(frozen=True, slots=True)
class EntityEdit(_Value):
    """Exactly one current revision and its append-only history record."""

    after: EntityAfter
    history: Encoded
    occurred_at: str
    history_kind: Literal["metadata"] = "metadata"


@dataclass(frozen=True, slots=True)
class MemberChange(_Value):
    """One ordered raw occurrence; None deletes, JSON null is a real entry."""

    run_id: str
    ordinal: int
    after: Encoded | None

    def __post_init__(self) -> None:
        _Value.__post_init__(self)
        text(self.run_id, required=True)
        integer(self.ordinal)


@dataclass(frozen=True, slots=True)
class EventDraft(_Value):
    """Stable event identity; insertion is atomic, external emission is absent."""

    event_id: str
    ordinal: int
    event_type: str
    envelope: Encoded

    def __post_init__(self) -> None:
        _Value.__post_init__(self)
        text(self.event_id, required=True)
        integer(self.ordinal)


@dataclass(frozen=True, slots=True)
class DeliveryDraft(_Value):
    """Immutable draft only; no physical object or publication proof implied."""

    step_id: str
    ordinal: int
    target_kind: Literal["yaml", "derived", "event", "dispatch"]
    target_key: str
    target_revision: int
    payload: Encoded
    due_at: str

    def __post_init__(self) -> None:
        _Value.__post_init__(self)
        text(self.step_id, required=True)
        integer(self.ordinal)


@dataclass(frozen=True, slots=True, init=False)
class PreparedObject(_Value):
    """Trusted host result, issued only after ProjectObjectStore.publish returns.

    The composition owns exact authorization, directory durability and exclusion
    of object mutation/redirection through commit. This is not a public proof or
    a deserializable capability. A descriptor constructor cannot assert durability.
    """

    binding: StoreBinding
    ref: ObjectRef

    def __init__(self) -> None:
        raise MutationError("mutation_prepare_required")

    @classmethod
    def prepare(
        cls,
        store: ProjectObjectStore,
        binding: StoreBinding,
        ref: ObjectRef,
        chunks: Iterable[bytes],
    ) -> PreparedObject:
        if type(store) is not ProjectObjectStore or type(binding) is not StoreBinding:
            raise MutationError("mutation_input_invalid")
        if type(ref) is not ObjectRef:
            raise MutationError("mutation_input_invalid")
        store.publish(ref, chunks)
        value = object.__new__(cls)
        object.__setattr__(value, "binding", binding)
        object.__setattr__(value, "ref", ref)
        _Value.__post_init__(value)
        return value

    @property
    def relative_path(self) -> str:
        return object_relative_path(self.ref).as_posix()

    @property
    def object_id(self) -> str:
        from .mutation_codec import digest, encode

        return digest(encode((self.binding.project_id, self.relative_path)))


@dataclass(frozen=True, slots=True)
class EntityFileUse(_Value):
    """Exact revision association; semantic metadata belongs to its history."""

    binding: StoreBinding
    key: EntityKey
    revision: int
    object_id: str
    role: str
    ordinal: int
    codec: str
    media_type: str
    logical_reference: str
    evidence_status: str

    def __post_init__(self) -> None:
        _Value.__post_init__(self)
        integer(self.revision, 1)
        integer(self.ordinal)
        for value in (self.object_id, self.role, self.codec, self.media_type):
            text(value, required=True)
        if self.codec != "raw.v1" and (
            self.codec not in ("pf.context-fragment.v1", "pf.context-manifest.v1")
            or self.media_type != "application/json"
        ):
            raise MutationError("mutation_codec_unsupported")


@dataclass(frozen=True, slots=True)
class ImmutableLinkDraft(_Value):
    """Inert closed association-aware draft; physical publication is absent."""

    step_id: str
    ordinal: int
    use: EntityFileUse
    target_key: str
    due_at: str

    def __post_init__(self) -> None:
        _Value.__post_init__(self)
        integer(self.ordinal)
        text(self.step_id, required=True)
        from .mutation_codec import target_path

        target_path(self.target_key)


@dataclass(frozen=True, slots=True)
class AssociationMetadata(_Value):
    """Detached metadata, conveying no body-read permission."""

    use: EntityFileUse
    ref: ObjectRef
    relative_path: str


@dataclass(frozen=True, slots=True)
class MutationPlan(_Value):
    """Closed internal metadata edit, prepared outside the write transaction.

    Domain planning must validate process semantics and current host authority.
    This kernel checks storage invariants and exact read revisions only.
    """

    operation_id: str
    client_key: str | None
    request: Encoded
    accepted: Encoded
    receipt: Encoded
    proof: ReadProof
    entities: tuple[EntityEdit, ...]
    members: tuple[MemberChange, ...] = ()
    events: tuple[EventDraft, ...] = ()
    deliveries: tuple[DeliveryDraft, ...] = ()
    operation_kind: Literal["metadata"] = "metadata"
    origin: Literal["client", "internal"] = "internal"
    objects: tuple[PreparedObject, ...] = ()
    uses: tuple[EntityFileUse, ...] = ()
    immutable_links: tuple[ImmutableLinkDraft, ...] = ()

    def __post_init__(self) -> None:
        _Value.__post_init__(self)
        text(self.operation_id, required=True)
        if not self.entities:
            raise MutationError("mutation_empty")
        groups = (
            tuple(o.object_id for o in self.objects),
            tuple((u.key, u.revision, u.role, u.ordinal) for u in self.uses),
            tuple(e.after.key for e in self.entities),
            tuple(e.key for e in self.proof.entities),
            tuple((m.run_id, m.ordinal) for m in self.members),
            tuple(e.event_id for e in self.events),
            tuple(e.ordinal for e in self.events),
            tuple(d.step_id for d in self.deliveries)
            + tuple(d.step_id for d in self.immutable_links),
            tuple(d.ordinal for d in self.deliveries)
            + tuple(d.ordinal for d in self.immutable_links),
        )
        if any(len(set(group)) != len(group) for group in groups):
            raise MutationError("mutation_duplicate_identity")
        read_keys = {e.key for e in self.proof.entities}
        changed = {e.after.key for e in self.entities}
        if not changed <= read_keys or any(
            EntityKey("run", m.run_id) not in changed for m in self.members
        ):
            raise MutationError("mutation_read_set_incomplete")


@dataclass(frozen=True, slots=True)
class AcceptedReceipt(_Value):
    """Immutable accepted identity, independent of mutable delivery progress."""

    operation_id: str
    accepted_seq: int
    receipt: Encoded


@dataclass(frozen=True, slots=True)
class DeliveryState(_Value):
    """Detached mutable delivery state returned separately from the receipt."""

    revision: int
    state: Literal["pending", "applied", "blocked"]
    pending_steps: int
    next_due_at: str
    last_error_code: str


@dataclass(frozen=True, slots=True)
class MutationResult(_Value):
    """Accepted only after commit, or recovered from an exact stored operation."""

    acceptance: Literal["accepted", "replayed"]
    receipt: AcceptedReceipt
    delivery: DeliveryState


@dataclass(frozen=True, slots=True)
class HistoryRecord(_Value):
    """Keyset record identity includes sequence, revision and explicit codec."""

    seq: int
    operation_id: str
    key: EntityKey
    entity_revision: int
    body: Encoded
    history_kind: str
    occurred_at: str


@dataclass(frozen=True, slots=True)
class HistoryPage(_Value):
    """Bounded internal history page; cursor is a sequence, never an offset."""

    records: tuple[HistoryRecord, ...]
    next_seq: int | None
