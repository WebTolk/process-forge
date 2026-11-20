"""Strict CJ1 and storage-v2 primitives without registry or filesystem access.

Callers supply an already domain-validated semantic document for packing.
Decoding verifies storage, the pinned semantic schema and frozen bindings;
current execution admission, source drift and readiness remain caller duties.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any

from .compact_model import (
    INT_MAX,
    INT_MIN,
    MAX_BYTES,
    MAX_NESTING,
    CapsuleIdentity,
    CompactError,
    CompactPlan,
    JsonValue,
    ObjectRef,
    VerifiedCapsule,
    _freeze,
)

_JSON = "application/json"
_MANIFEST = "pf.context-manifest.v1"
_FRAGMENT = "pf.context-fragment.v1"
_FEATURES = ("compact_fragments_v1", "portable_material_v1")
_REF_KEYS = {"algorithm", "digest", "size", "media_type", "codec"}
_IDENTITY_KEYS = {"project_uuid", "project_id", "run_id", "assignment_id", "context_id"}
_CAPSULE_KEYS = {
    "id",
    "assignment_id",
    "assignment_path",
    "immutable",
    "worker_may_rebuild_context",
    "generated_at",
}
_MATERIAL_KEYS = {
    "resource_id",
    "role",
    "access",
    "object",
    "original_checksum",
    "required",
    "interpretation_version",
}
_ROLES = {
    "instruction",
    "process_definition",
    "knowledge",
    "template",
    "source_snapshot",
    "descriptor",
}


def _plain(value: JsonValue) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_plain(child) for child in value]
    return value


def canonical_bytes(value: JsonValue) -> bytes:
    """Encode CJ1, bounded to the disconnected capsule profile's 2 MiB."""
    plain = _plain(_freeze(value))
    encoder = json.JSONEncoder(
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    result = bytearray()
    for part in encoder.iterencode(plain):
        encoded = part.encode("utf-8")
        if len(result) + len(encoded) > MAX_BYTES:
            raise CompactError("size_limit")
        result.extend(encoded)
    return bytes(result)


def _depth(raw: bytes) -> None:
    depth = 0
    quoted = escaped = False
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            if depth > MAX_NESTING:
                raise CompactError("nesting_limit")
        elif char in (93, 125):
            depth -= 1


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CompactError("duplicate_key")
        result[key] = value
    return result


def _integer(text: str) -> int:
    if len(text) > 20:
        raise CompactError("integer_overflow")
    result = int(text)
    if not INT_MIN <= result <= INT_MAX:
        raise CompactError("integer_overflow")
    return result


def _not_number(text: str) -> None:
    raise CompactError("unsupported_number")


def decode_canonical(raw: bytes) -> JsonValue:
    """Decode strict canonical UTF-8 JSON, rejecting ambiguity before use."""
    if type(raw) is not bytes:
        raise CompactError("invalid_bytes")
    if len(raw) > MAX_BYTES:
        raise CompactError("size_limit")
    _depth(raw)
    try:
        decoded = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_int=_integer,
            parse_float=_not_number,
            parse_constant=_not_number,
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise CompactError("invalid_json") from None
    frozen = _freeze(decoded)
    if canonical_bytes(frozen) != raw:
        raise CompactError("noncanonical_json")
    return frozen


def _checksum(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def object_ref(raw: bytes, *, media_type: str, codec: str) -> ObjectRef:
    """Describe exact bytes; this does not grant access or decode content."""
    if type(raw) is not bytes:
        raise CompactError("invalid_bytes")
    return ObjectRef(
        "sha256", hashlib.sha256(raw).hexdigest(), len(raw), media_type, codec
    )


def _map(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CompactError("invalid_shape")
    return value


def _exact(value: object, keys: set[str]) -> Mapping[str, Any]:
    result = _map(value)
    if set(result) != keys:
        raise CompactError("invalid_shape")
    return result


def _ref(value: object) -> ObjectRef:
    return ObjectRef(**_exact(value, _REF_KEYS))


def _same_ref(ref: ObjectRef, seen: dict[str, ObjectRef]) -> None:
    previous = seen.setdefault(ref.digest, ref)
    if previous != ref:
        raise CompactError("reference_metadata_mismatch")


def _codec(ref: ObjectRef, codec: str) -> None:
    if ref.codec != codec or ref.media_type != _JSON:
        raise CompactError("unsupported_codec")


def _leaf_data(value: JsonValue) -> None:
    # Object references are only legal in the manifest's explicit grammar.
    # No recursive reference resolver exists, even for well-formed digests.
    if isinstance(value, Mapping):
        if set(value) == _REF_KEYS:
            raise CompactError("recursive_reference")
        for child in value.values():
            _leaf_data(child)
    elif isinstance(value, tuple):
        for child in value:
            _leaf_data(child)


def _capsule(value: object, identity: CapsuleIdentity) -> Mapping[str, Any]:
    capsule = _exact(value, _CAPSULE_KEYS)
    if (
        capsule["id"] != identity.context_id
        or capsule["assignment_id"] != identity.assignment_id
        or capsule["assignment_path"]
        != f".pf/assignments/{identity.assignment_id}.yaml"
        or capsule["immutable"] is not True
        or capsule["worker_may_rebuild_context"] is not False
    ):
        raise CompactError("identity_mismatch")
    generated = capsule["generated_at"]
    if not isinstance(generated, str) or not re.fullmatch(
        r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|\+00:00)",
        generated,
    ):
        raise CompactError("invalid_timestamp")
    try:
        timestamp = datetime.fromisoformat(generated.replace("Z", "+00:00"))
    except ValueError:
        raise CompactError("invalid_timestamp") from None
    if timestamp.utcoffset() != timedelta(0):
        raise CompactError("invalid_timestamp")
    return capsule


def _schema_matches(value: Any, node: Any, root: Any) -> bool:
    """Evaluate the pinned semantic schema subset, with no external resolver."""
    if type(node) is bool:
        return node
    if "$ref" in node:
        ref = node["$ref"]
        if not ref.startswith("#/"):
            raise CompactError("unsupported_semantic_schema")
        target = root
        for token in ref[2:].split("/"):
            target = target[token.replace("~1", "/").replace("~0", "~")]
        return _schema_matches(value, target, root)
    known = {
        "$schema",
        "$id",
        "$defs",
        "title",
        "description",
        "default",
        "type",
        "const",
        "enum",
        "minimum",
        "maximum",
        "minLength",
        "maxLength",
        "pattern",
        "minItems",
        "maxItems",
        "uniqueItems",
        "minProperties",
        "maxProperties",
        "required",
        "properties",
        "additionalProperties",
        "items",
        "allOf",
        "anyOf",
        "oneOf",
        "not",
        "if",
        "then",
        "else",
    }
    if set(node) - known:
        raise CompactError("unsupported_semantic_schema")
    types = {
        "null": value is None,
        "boolean": type(value) is bool,
        "integer": type(value) is int,
        "number": type(value) is int,
        "string": type(value) is str,
        "object": isinstance(value, Mapping),
        "array": isinstance(value, tuple),
    }
    if "type" in node:
        allowed = node["type"]
        allowed = (allowed,) if isinstance(allowed, str) else allowed
        if not any(types.get(kind, False) for kind in allowed):
            return False
    if "const" in node and canonical_bytes(value) != canonical_bytes(node["const"]):
        return False
    if "enum" in node and not any(
        canonical_bytes(value) == canonical_bytes(choice) for choice in node["enum"]
    ):
        return False
    for keyword, predicate in (
        ("allOf", all),
        ("anyOf", any),
    ):
        if keyword in node and not predicate(
            _schema_matches(value, child, root) for child in node[keyword]
        ):
            return False
    if (
        "oneOf" in node
        and sum(_schema_matches(value, child, root) for child in node["oneOf"]) != 1
    ):
        return False
    if "not" in node and _schema_matches(value, node["not"], root):
        return False
    if "if" in node:
        branch = "then" if _schema_matches(value, node["if"], root) else "else"
        if branch in node and not _schema_matches(value, node[branch], root):
            return False
    if type(value) is int:
        if "minimum" in node and value < node["minimum"]:
            return False
        if "maximum" in node and value > node["maximum"]:
            return False
    if isinstance(value, (str, tuple, Mapping)):
        if isinstance(value, str):
            low, high = "minLength", "maxLength"
        elif isinstance(value, tuple):
            low, high = "minItems", "maxItems"
        else:
            low, high = "minProperties", "maxProperties"
        if low in node and len(value) < node[low]:
            return False
        if high in node and len(value) > node[high]:
            return False
    if isinstance(value, str) and "pattern" in node:
        if not re.fullmatch(node["pattern"], value):
            return False
    if isinstance(value, tuple):
        if node.get("uniqueItems"):
            encoded = [canonical_bytes(child) for child in value]
            if len(set(encoded)) != len(encoded):
                return False
        if "items" in node and not all(
            _schema_matches(child, node["items"], root) for child in value
        ):
            return False
    if isinstance(value, Mapping):
        if any(key not in value for key in node.get("required", ())):
            return False
        properties = node.get("properties", {})
        for key, child in value.items():
            schema = properties.get(key, node.get("additionalProperties", True))
            if not _schema_matches(child, schema, root):
                return False
    return True


def _semantic(document: Mapping[str, Any], identity: CapsuleIdentity) -> None:
    """Check frozen bindings and the existing compact semantic SHA formula.

    The embedded schema is pinned to the reviewed source, never loaded from
    the host. validate_execution_contract reads current files/capabilities;
    its execution admission responsibilities remain outside this decoder.
    """
    required = {
        "schema_version",
        "capsule",
        "assignment",
        "context",
        "process_execution",
        "context_snapshot",
        "resource_bindings",
        "execution_contract",
    }
    if not required.issubset(document):
        raise CompactError("semantic_document_invalid")
    schema = _SEMANTIC_SCHEMA
    if not _schema_matches(document, schema, schema):
        raise CompactError("semantic_schema_invalid")
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise CompactError("semantic_document_invalid")
    _capsule(document["capsule"], identity)
    assignment = _map(document["assignment"])
    if (
        assignment.get("id") != identity.assignment_id
        or assignment.get("run_id") != identity.run_id
        or assignment.get("path") != f".pf/assignments/{identity.assignment_id}.yaml"
    ):
        raise CompactError("identity_mismatch")
    if "identity" in document and document["identity"] != asdict(identity):
        raise CompactError("identity_mismatch")
    contract = _map(document["execution_contract"])
    contract_required = {
        "contract_version",
        "identity",
        "assignment_intent",
        "assignment_intent_checksum",
        "snapshot",
        "process",
        "resources",
        "scope",
        "required_sources",
        "outputs",
        "capabilities",
        "workspace_access",
        "parameters",
        "coordination",
        "source_limits",
        "readiness",
        "worker_may_rebuild_context",
        "contract_checksum",
    }
    if not contract_required.issubset(contract):
        raise CompactError("semantic_contract_invalid")
    if (
        type(contract["contract_version"]) is not int
        or contract["contract_version"] not in (1, 2)
        or contract["worker_may_rebuild_context"] is not False
    ):
        raise CompactError("semantic_contract_invalid")
    binding = _map(contract["identity"])
    expected = asdict(identity)
    expected.pop("project_uuid")
    if binding != {"kind": "work", **expected}:
        raise CompactError("identity_mismatch")
    if (
        _checksum(
            canonical_bytes(
                {
                    key: value
                    for key, value in contract.items()
                    if key != "contract_checksum"
                }
            )
        )
        != contract["contract_checksum"]
    ):
        raise CompactError("contract_checksum_mismatch")
    intent = _map(contract["assignment_intent"])
    if _checksum(canonical_bytes(intent)) != contract["assignment_intent_checksum"]:
        raise CompactError("intent_checksum_mismatch")
    for key in ("outputs", "workspace_access"):
        if (
            key not in document
            or document[key] != contract[key]
            or intent.get(key) != contract[key]
        ):
            raise CompactError("semantic_binding_mismatch")
    scope = dict(_map(contract["scope"]))
    scope["non_overlap"] = dict(_map(scope.get("non_overlap")))
    scope["non_overlap"].pop("overlap_check", None)
    if document.get("scope") != contract["scope"] or scope != intent.get("scope"):
        raise CompactError("semantic_binding_mismatch")
    context = _map(document["context"])
    resources = _map(contract["resources"])
    if resources.get("bindings_checksum") != _checksum(
        canonical_bytes(document["resource_bindings"])
    ) or resources.get("selected_ids") != context.get("selected_resource_ids"):
        raise CompactError("semantic_binding_mismatch")
    snapshot = _map(document["context_snapshot"])
    if contract["snapshot"] != {
        "id": snapshot.get("id"),
        "checksum": snapshot.get("sha256"),
    }:
        raise CompactError("semantic_binding_mismatch")
    pin = _map(document["process_execution"])
    if pin.get("process_fingerprint") != _checksum(
        canonical_bytes(pin.get("definition"))
    ) or contract["process"] != {
        "id": pin.get("process_id"),
        "version": pin.get("process_version"),
        "fingerprint": pin.get("process_fingerprint"),
    }:
        raise CompactError("process_checksum_mismatch")


def _materials(
    value: object, seen: dict[str, ObjectRef]
) -> tuple[Mapping[str, JsonValue], ...]:
    if not isinstance(value, tuple):
        raise CompactError("invalid_material")
    result = []
    keys = set()
    for item in value:
        record = _exact(item, _MATERIAL_KEYS)
        for key in (
            "resource_id",
            "role",
            "access",
            "original_checksum",
            "interpretation_version",
        ):
            if type(record[key]) is not str or not record[key]:
                raise CompactError("invalid_material")
        if (
            record["role"] not in _ROLES
            or record["access"] not in ("body", "metadata")
            or type(record["required"]) is not bool
        ):
            raise CompactError("invalid_material")
        if record["access"] == "metadata" and record["role"] != "descriptor":
            raise CompactError("metadata_body_reference")
        ref = _ref(record["object"])
        if ref.codec != "raw.v1":
            raise CompactError("unsupported_codec")
        _same_ref(ref, seen)
        material_key = (record["resource_id"], record["role"], record["access"])
        if material_key in keys:
            raise CompactError("duplicate_material")
        keys.add(material_key)
        result.append(record)
    return tuple(result)


def _escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _tokens(target: object) -> tuple[str, ...]:
    if type(target) is not str or not target.startswith("/"):
        raise CompactError("invalid_pointer")
    tokens = tuple(
        part.replace("~1", "/").replace("~0", "~") for part in target[1:].split("/")
    )
    if "/" + "/".join(_escape(part) for part in tokens) != target:
        raise CompactError("invalid_pointer")
    if len(tokens) > MAX_NESTING:
        raise CompactError("nesting_limit")
    return tokens


def _targets(
    value: object, seen: dict[str, ObjectRef]
) -> list[tuple[tuple[str, ...], ObjectRef]]:
    if not isinstance(value, tuple) or not value:
        raise CompactError("invalid_fragments")
    trie: dict[str, Any] = {}
    result = []
    previous: bytes | None = None
    expanded_size = 2
    for item in value:
        record = _exact(item, {"target", "object"})
        tokens = _tokens(record["target"])
        target_bytes = record["target"].encode("utf-8")
        if previous is not None and previous >= target_bytes:
            raise CompactError("fragment_order")
        previous = target_bytes
        ref = _ref(record["object"])
        _codec(ref, _FRAGMENT)
        _same_ref(ref, seen)
        node = trie
        for index, token in enumerate(tokens):
            last = index == len(tokens) - 1
            if token in node:
                if node[token] is None or last:
                    raise CompactError("expansion_collision")
            else:
                expanded_size += len(canonical_bytes(token)) + 1 + bool(node)
                expanded_size += ref.size if last else 2
                if expanded_size > MAX_BYTES:
                    raise CompactError("expansion_size_limit")
                node[token] = None if last else {}
            node = node[token]
        result.append((tokens, ref))
    return result


def pack_capsule(
    *,
    identity: CapsuleIdentity,
    document: Mapping[str, JsonValue],
    material: tuple[Mapping[str, JsonValue], ...],
) -> CompactPlan:
    """Pack a validated semantic v1 document; publish nothing and call no clock."""
    if type(identity) is not CapsuleIdentity:
        raise CompactError("invalid_identity")
    frozen = _map(_freeze(document))
    canonical_bytes(frozen)
    _semantic(frozen, identity)
    _leaf_data(frozen)
    seen: dict[str, ObjectRef] = {}
    materials = _materials(_freeze(material), seen)
    objects: dict[str, tuple[ObjectRef, bytes]] = {}

    def add(value: JsonValue, codec: str) -> ObjectRef:
        raw = canonical_bytes(value)
        ref = object_ref(raw, media_type=_JSON, codec=codec)
        _same_ref(ref, seen)
        if ref.digest in objects and objects[ref.digest][1] != raw:
            raise CompactError("object_collision")
        objects[ref.digest] = (ref, raw)
        return ref

    fragments: list[dict[str, Any]] = []
    pieces: Iterable[tuple[str, Any]]
    for key, value in frozen.items():
        target = "/" + _escape(key)
        if (
            key in ("execution_contract", "process_execution", "context")
            and isinstance(value, Mapping)
            and value
        ):
            pieces = (
                (target + "/" + _escape(child), body) for child, body in value.items()
            )
        else:
            pieces = ((target, value),)
        for pointer, body in pieces:
            fragments.append(
                {"target": pointer, "object": asdict(add(body, _FRAGMENT))}
            )
    fragments.sort(key=lambda item: item["target"].encode("utf-8"))
    _targets(_freeze(fragments), seen)
    manifest_ref = add(
        _freeze(
            {
                "version": 1,
                "kind": "pf.context-manifest",
                "identity": asdict(identity),
                "fragments": fragments,
                "material": materials,
            }
        ),
        _MANIFEST,
    )
    if (
        manifest_ref.size + sum(item["object"]["size"] for item in fragments)
        > MAX_BYTES
    ):
        raise CompactError("closure_size_limit")
    envelope = canonical_bytes(
        {
            "schema_version": 2,
            "kind": "pf.assignment-capsule",
            "reader_floor": 2,
            "writer_floor": 2,
            "required_features": _FEATURES,
            "identity": asdict(identity),
            "capsule": frozen["capsule"],
            "manifest": asdict(manifest_ref),
        }
    )
    return CompactPlan(
        envelope, _checksum(envelope), tuple(objects[key] for key in sorted(objects))
    )


def decode_capsule(
    *,
    raw: bytes,
    expected_checksum: str,
    expected_identity: CapsuleIdentity,
    read_object: Callable[[ObjectRef], bytes],
) -> VerifiedCapsule:
    """Verify a v2 physical pin before reference disclosure or object reads.

    read_object must authorize each exact reference before bounded file I/O.
    Material bodies are never fetched or inserted into the semantic document.
    """
    if type(raw) is not bytes or len(raw) > MAX_BYTES:
        raise CompactError("size_limit")
    if type(expected_checksum) is not str or not re.fullmatch(
        r"sha256:[a-f0-9]{64}", expected_checksum
    ):
        raise CompactError("invalid_checksum")
    if _checksum(raw) != expected_checksum:
        raise CompactError("capsule_checksum_mismatch")
    if type(expected_identity) is not CapsuleIdentity:
        raise CompactError("invalid_identity")
    envelope = _exact(
        decode_canonical(raw),
        {
            "schema_version",
            "kind",
            "reader_floor",
            "writer_floor",
            "required_features",
            "identity",
            "capsule",
            "manifest",
        },
    )
    if any(
        type(envelope[key]) is not int or envelope[key] != 2
        for key in ("schema_version", "reader_floor", "writer_floor")
    ):
        raise CompactError("unsupported_storage")
    if (
        envelope["kind"] != "pf.assignment-capsule"
        or envelope["required_features"] != _FEATURES
    ):
        raise CompactError("unsupported_features")
    identity = CapsuleIdentity(**_exact(envelope["identity"], _IDENTITY_KEYS))
    if identity != expected_identity:
        raise CompactError("identity_mismatch")
    _capsule(envelope["capsule"], identity)
    manifest_ref = _ref(envelope["manifest"])
    _codec(manifest_ref, _MANIFEST)
    seen: dict[str, ObjectRef] = {}
    _same_ref(manifest_ref, seen)

    def fetch(ref: ObjectRef) -> JsonValue:
        if ref.size > MAX_BYTES:
            raise CompactError("size_limit")
        body = read_object(ref)
        if type(body) is not bytes or len(body) != ref.size:
            raise CompactError("object_size_mismatch")
        if hashlib.sha256(body).hexdigest() != ref.digest:
            raise CompactError("object_hash_mismatch")
        return decode_canonical(body)

    manifest = _exact(
        fetch(manifest_ref), {"version", "kind", "identity", "fragments", "material"}
    )
    if (
        type(manifest["version"]) is not int
        or manifest["version"] != 1
        or manifest["kind"] != "pf.context-manifest"
    ):
        raise CompactError("unsupported_manifest")
    if _exact(manifest["identity"], _IDENTITY_KEYS) != asdict(identity):
        raise CompactError("identity_mismatch")
    materials = _materials(manifest["material"], seen)
    targets = _targets(manifest["fragments"], seen)
    if manifest_ref.size + sum(ref.size for _, ref in targets) > MAX_BYTES:
        raise CompactError("closure_size_limit")
    document: dict[str, Any] = {}
    for tokens, ref in targets:
        value = fetch(ref)
        _leaf_data(value)
        node = document
        for token in tokens[:-1]:
            node = node.setdefault(token, {})
        node[tokens[-1]] = value
    canonical_bytes(document)
    _semantic(document, identity)
    if document["capsule"] != envelope["capsule"]:
        raise CompactError("identity_mismatch")
    return VerifiedCapsule(2, identity, expected_checksum, document, materials)


# Pinned context-capsule schema from the reviewed frozen source.
# Data only: no filesystem, registry or external-reference resolution.
_SEMANTIC_SCHEMA_JSON = r"""{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://processforge.local/schemas/context-capsule.schema.json",
  "title": "Context Capsule",
  "type": "object",
  "required": [
    "schema_version",
    "capsule",
    "assignment",
    "context"
  ],
  "properties": {
    "schema_version": {
      "type": "integer",
      "minimum": 1
    },
    "capsule": {
      "type": "object",
      "required": [
        "id",
        "worker_may_rebuild_context"
      ],
      "properties": {
        "id": {
          "$ref": "#/$defs/id"
        },
        "ecp": {
          "type": "string"
        },
        "generated_at": {
          "type": "string"
        },
        "assignment_id": {
          "type": "string"
        },
        "assignment_path": {
          "type": "string"
        },
        "assignment_checksum": {
          "type": "string"
        },
        "snapshot": {
          "type": "string"
        },
        "snapshot_checksum": {
          "type": "string"
        },
        "immutable": {
          "type": "boolean"
        },
        "worker_may_rebuild_context": {
          "type": "boolean"
        }
      },
      "additionalProperties": true
    },
    "assignment": {
      "type": "object",
      "additionalProperties": true
    },
    "resource_bindings": {
      "$ref": "#/$defs/resource_bindings"
    },
    "execution_contract": {
      "$ref": "#/$defs/execution_contract"
    },
    "context_snapshot": {
      "type": "object",
      "required": [
        "id",
        "sha256",
        "freshness_at_creation"
      ],
      "properties": {
        "id": {
          "type": "string",
          "minLength": 1
        },
        "sha256": {
          "type": "string",
          "minLength": 1
        },
        "generated_at": {
          "type": [
            "string",
            "null"
          ]
        },
        "freshness_at_creation": {
          "enum": [
            "fresh",
            "fresh_with_updates",
            "stale",
            "broken"
          ]
        }
      },
      "additionalProperties": true
    },
    "project_classification": {
      "type": "object",
      "additionalProperties": true
    },
    "resolved_resources": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true
      }
    },
    "resolved_parameters": {
      "type": "object",
      "additionalProperties": true
    },
    "parameter_resolution_summary": {
      "type": "object",
      "additionalProperties": true
    },
    "effective_specializations": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true
      }
    },
    "project_override_summary": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true
      }
    },
    "active_resource_profile": {
      "type": "object",
      "additionalProperties": true
    },
    "execution_route_summary": {
      "type": "object",
      "additionalProperties": true
    },
    "capability_resolution_summary": {
      "type": "object",
      "additionalProperties": true
    },
    "effective_resources": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true
      }
    },
    "context": {
      "type": "object",
      "properties": {
        "snapshot_id": {
          "type": "string"
        },
        "freshness": {
          "type": "string"
        },
        "required_sources": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "context_artifacts": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/context_artifact"
          }
        },
        "selected_specializations": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "selected_resource_ids": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "applied_project_overrides": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      },
      "additionalProperties": true
    },
    "scope": {
      "type": "object",
      "properties": {
        "allowed_files": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "allowed_read_files": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "forbidden_files": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "ownership": {
          "$ref": "#/$defs/ownership"
        },
        "non_overlap": {
          "type": "object",
          "additionalProperties": true
        }
      },
      "additionalProperties": true
    },
    "outputs": {
      "type": "object",
      "properties": {
        "required_outputs": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/required_output"
          }
        },
        "expected_report": {
          "type": "object",
          "additionalProperties": true
        }
      },
      "additionalProperties": true
    },
    "capabilities": {
      "type": "object",
      "properties": {
        "required": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "optional": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": true
          }
        }
      },
      "additionalProperties": true
    },
    "required_sources": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "allowed_files": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "forbidden_files": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "required_outputs": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/required_output"
      }
    },
    "required_capabilities": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true
      }
    },
    "optional_capabilities": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true
      }
    },
    "selected_sources": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "telemetry": {
      "type": "object",
      "additionalProperties": true
    },
    "event_correlation_id": {
      "type": "string"
    },
    "allowed_actions": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "forbidden_actions": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "$defs": {
    "execution_contract": {
      "description": "Complete versioned immutable assignment intent and worker permission block. The context capsule schema leaves this block optional for legacy capsules.",
      "type": "object",
      "required": [
        "contract_version",
        "identity",
        "assignment_intent",
        "assignment_intent_checksum",
        "snapshot",
        "process",
        "resources",
        "scope",
        "required_sources",
        "outputs",
        "capabilities",
        "workspace_access",
        "parameters",
        "coordination",
        "source_limits",
        "readiness",
        "worker_may_rebuild_context",
        "contract_checksum"
      ],
      "properties": {
        "contract_version": {
          "enum": [
            1,
            2
          ]
        },
        "identity": {
          "type": "object",
          "required": [
            "kind",
            "project_id",
            "run_id",
            "assignment_id",
            "context_id"
          ],
          "properties": {
            "kind": {
              "enum": [
                "work",
                "assignment"
              ]
            },
            "project_id": {
              "type": "string",
              "minLength": 1
            },
            "run_id": {
              "type": "string"
            },
            "assignment_id": {
              "type": "string",
              "minLength": 1
            },
            "context_id": {
              "type": "string",
              "minLength": 1
            }
          },
          "additionalProperties": false
        },
        "assignment_intent": {
          "$ref": "#/$defs/execution_contract/$defs/assignment_intent"
        },
        "assignment_intent_checksum": {
          "$ref": "#/$defs/execution_contract/$defs/digest"
        },
        "snapshot": {
          "type": "object",
          "required": [
            "id",
            "checksum"
          ],
          "properties": {
            "id": {
              "type": "string",
              "minLength": 1
            },
            "checksum": {
              "$ref": "#/$defs/execution_contract/$defs/digest"
            }
          },
          "additionalProperties": false
        },
        "process": {
          "type": "object",
          "required": [
            "id",
            "version",
            "fingerprint"
          ],
          "properties": {
            "id": {
              "type": "string"
            },
            "version": {
              "type": "string"
            },
            "fingerprint": {
              "type": "string",
              "pattern": "^(?:sha256:[a-f0-9]{64})?$"
            }
          },
          "additionalProperties": false
        },
        "resources": {
          "type": "object",
          "required": [
            "selected_ids",
            "bindings_checksum"
          ],
          "properties": {
            "selected_ids": {
              "type": "array",
              "items": {
                "type": "string"
              }
            },
            "bindings_checksum": {
              "$ref": "#/$defs/execution_contract/$defs/digest"
            }
          },
          "additionalProperties": false
        },
        "scope": {
          "$ref": "#/$defs/execution_contract/$defs/scope"
        },
        "required_sources": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/execution_contract/$defs/required_source"
          }
        },
        "outputs": {
          "$ref": "#/$defs/execution_contract/$defs/outputs"
        },
        "capabilities": {
          "type": "object",
          "required": [
            "required",
            "optional"
          ],
          "properties": {
            "required": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/execution_contract/$defs/capability"
              }
            },
            "optional": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/execution_contract/$defs/capability"
              }
            }
          },
          "additionalProperties": false
        },
        "workspace_access": {
          "type": "object",
          "additionalProperties": {
            "type": "array"
          }
        },
        "parameters": {
          "type": "object",
          "additionalProperties": true
        },
        "coordination": {
          "type": "object",
          "additionalProperties": true
        },
        "worker_may_rebuild_context": {
          "const": false
        },
        "source_limits": {
          "type": "object",
          "required": [
            "files",
            "file_bytes",
            "total_bytes"
          ],
          "properties": {
            "files": {
              "type": "integer",
              "minimum": 1
            },
            "file_bytes": {
              "type": "integer",
              "minimum": 1
            },
            "total_bytes": {
              "type": "integer",
              "minimum": 1
            }
          },
          "additionalProperties": false
        },
        "readiness": {
          "type": "object",
          "required": [
            "status",
            "blockers"
          ],
          "properties": {
            "status": {
              "enum": [
                "ready",
                "blocked"
              ]
            },
            "blockers": {
              "type": "array",
              "items": {
                "type": "object",
                "required": [
                  "code"
                ],
                "properties": {
                  "code": {
                    "type": "string",
                    "minLength": 1
                  }
                },
                "additionalProperties": true
              }
            }
          },
          "additionalProperties": false
        },
        "contract_checksum": {
          "$ref": "#/$defs/execution_contract/$defs/digest"
        },
        "egress": {
          "type": "object",
          "required": [
            "policy_id",
            "recipient",
            "purpose",
            "policy_checksum",
            "detector_checksum",
            "minimum_enforcement",
            "limits"
          ],
          "properties": {
            "policy_id": {
              "type": "string",
              "pattern": "^[a-z][a-z0-9-]{0,63}$"
            },
            "recipient": {
              "type": "string",
              "pattern": "^[a-z][a-z0-9-]{0,63}$"
            },
            "purpose": {
              "type": "string",
              "pattern": "^[a-z][a-z0-9-]{0,63}$"
            },
            "policy_checksum": {
              "type": "string",
              "pattern": "^sha256:[a-f0-9]{64}$"
            },
            "detector_checksum": {
              "type": "string",
              "pattern": "^sha256:[a-f0-9]{64}$"
            },
            "minimum_enforcement": {
              "const": "mediated_session"
            },
            "limits": {
              "type": "object",
              "required": [
                "unit_bytes",
                "envelope_bytes",
                "attempt_bytes",
                "disclosures",
                "json_depth",
                "classification_ms",
                "token_seconds"
              ],
              "properties": {
                "unit_bytes": {
                  "type": "integer",
                  "minimum": 1,
                  "maximum": 1048576
                },
                "envelope_bytes": {
                  "type": "integer",
                  "minimum": 1,
                  "maximum": 4194304
                },
                "attempt_bytes": {
                  "type": "integer",
                  "minimum": 1,
                  "maximum": 33554432
                },
                "disclosures": {
                  "type": "integer",
                  "minimum": 1,
                  "maximum": 128
                },
                "json_depth": {
                  "type": "integer",
                  "minimum": 1,
                  "maximum": 16
                },
                "classification_ms": {
                  "type": "integer",
                  "minimum": 1,
                  "maximum": 2000
                },
                "token_seconds": {
                  "type": "integer",
                  "minimum": 1,
                  "maximum": 30
                }
              },
              "additionalProperties": false
            }
          },
          "additionalProperties": false
        }
      },
      "additionalProperties": false,
      "$defs": {
        "digest": {
          "type": "string",
          "pattern": "^sha256:[a-f0-9]{64}$"
        },
        "ownership": {
          "type": "object",
          "properties": {
            "owner_id": {
              "type": "string"
            },
            "owner_label": {
              "type": "string"
            },
            "role": {
              "type": "string"
            },
            "writer": {
              "type": "boolean"
            },
            "owned_files": {
              "type": "array",
              "items": {
                "type": "string"
              }
            },
            "owned_globs": {
              "type": "array",
              "items": {
                "type": "string"
              }
            }
          },
          "additionalProperties": true
        },
        "non_overlap": {
          "type": "object",
          "additionalProperties": true
        },
        "execution_mode": {
          "type": "object",
          "required": [
            "kind",
            "code_changes_allowed",
            "artifact_changes_allowed",
            "requires_review"
          ],
          "properties": {
            "kind": {
              "type": "string",
              "minLength": 1
            },
            "code_changes_allowed": {
              "type": "boolean"
            },
            "artifact_changes_allowed": {
              "type": "boolean"
            },
            "requires_review": {
              "type": "boolean"
            }
          },
          "additionalProperties": true
        },
        "outputs": {
          "type": "object",
          "required": [
            "required_outputs",
            "expected_report"
          ],
          "properties": {
            "required_outputs": {
              "type": "array",
              "items": {
                "oneOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "object",
                    "additionalProperties": true
                  }
                ]
              }
            },
            "expected_report": {
              "type": "object",
              "additionalProperties": true
            }
          },
          "additionalProperties": true
        },
        "scope": {
          "type": "object",
          "required": [
            "allowed_files",
            "allowed_read_files",
            "forbidden_files",
            "allowed_actions",
            "forbidden_actions",
            "ownership",
            "non_overlap"
          ],
          "properties": {
            "allowed_files": {
              "type": "array",
              "items": {
                "type": "string"
              }
            },
            "allowed_read_files": {
              "type": "array",
              "items": {
                "type": "string"
              }
            },
            "forbidden_files": {
              "type": "array",
              "items": {
                "type": "string"
              }
            },
            "allowed_actions": {
              "type": "array",
              "items": {
                "type": "string"
              }
            },
            "forbidden_actions": {
              "type": "array",
              "items": {
                "type": "string"
              }
            },
            "ownership": {
              "type": "object",
              "properties": {
                "owner_id": {
                  "type": "string"
                },
                "owner_label": {
                  "type": "string"
                },
                "role": {
                  "type": "string"
                },
                "writer": {
                  "type": "boolean"
                },
                "owned_files": {
                  "type": "array",
                  "items": {
                    "type": "string"
                  }
                },
                "owned_globs": {
                  "type": "array",
                  "items": {
                    "type": "string"
                  }
                }
              },
              "additionalProperties": true
            },
            "non_overlap": {
              "type": "object",
              "additionalProperties": true
            }
          },
          "additionalProperties": false
        },
        "assignment_intent": {
          "type": "object",
          "required": [
            "objective",
            "execution_mode",
            "scope",
            "required_sources",
            "context_artifacts",
            "outputs",
            "workspace_access",
            "subagent_policy",
            "required_capabilities",
            "optional_capabilities",
            "process",
            "selected_specializations",
            "coordination_requirements",
            "director_inbox_submit_required",
            "parameters",
            "allowed_tools",
            "allowed_templates",
            "selected_sources",
            "obligations"
          ],
          "properties": {
            "objective": {
              "type": "string"
            },
            "execution_mode": {
              "type": "object",
              "required": [
                "kind",
                "code_changes_allowed",
                "artifact_changes_allowed",
                "requires_review"
              ],
              "properties": {
                "kind": {
                  "type": "string",
                  "minLength": 1
                },
                "code_changes_allowed": {
                  "type": "boolean"
                },
                "artifact_changes_allowed": {
                  "type": "boolean"
                },
                "requires_review": {
                  "type": "boolean"
                }
              },
              "additionalProperties": true
            },
            "scope": {
              "type": "object",
              "required": [
                "allowed_files",
                "allowed_read_files",
                "forbidden_files",
                "allowed_actions",
                "forbidden_actions",
                "ownership",
                "non_overlap"
              ],
              "properties": {
                "allowed_files": {
                  "type": "array",
                  "items": {
                    "type": "string"
                  }
                },
                "allowed_read_files": {
                  "type": "array",
                  "items": {
                    "type": "string"
                  }
                },
                "forbidden_files": {
                  "type": "array",
                  "items": {
                    "type": "string"
                  }
                },
                "allowed_actions": {
                  "type": "array",
                  "items": {
                    "type": "string"
                  }
                },
                "forbidden_actions": {
                  "type": "array",
                  "items": {
                    "type": "string"
                  }
                },
                "ownership": {
                  "type": "object",
                  "properties": {
                    "owner_id": {
                      "type": "string"
                    },
                    "owner_label": {
                      "type": "string"
                    },
                    "role": {
                      "type": "string"
                    },
                    "writer": {
                      "type": "boolean"
                    },
                    "owned_files": {
                      "type": "array",
                      "items": {
                        "type": "string"
                      }
                    },
                    "owned_globs": {
                      "type": "array",
                      "items": {
                        "type": "string"
                      }
                    }
                  },
                  "additionalProperties": true
                },
                "non_overlap": {
                  "type": "object",
                  "additionalProperties": true
                }
              },
              "additionalProperties": false
            },
            "required_sources": {
              "type": "array",
              "items": {
                "type": "string"
              }
            },
            "context_artifacts": {
              "type": "array",
              "items": {
                "type": "object",
                "additionalProperties": true
              }
            },
            "outputs": {
              "type": "object",
              "required": [
                "required_outputs",
                "expected_report"
              ],
              "properties": {
                "required_outputs": {
                  "type": "array",
                  "items": {
                    "oneOf": [
                      {
                        "type": "string"
                      },
                      {
                        "type": "object",
                        "additionalProperties": true
                      }
                    ]
                  }
                },
                "expected_report": {
                  "type": "object",
                  "additionalProperties": true
                }
              },
              "additionalProperties": true
            },
            "workspace_access": {
              "type": "object",
              "additionalProperties": {
                "type": "array"
              }
            },
            "subagent_policy": {
              "type": "object",
              "additionalProperties": true
            },
            "required_capabilities": {
              "type": "array",
              "items": {
                "type": "string"
              }
            },
            "optional_capabilities": {
              "type": "array",
              "items": {
                "type": "string"
              }
            },
            "process": {
              "oneOf": [
                {
                  "type": "string"
                },
                {
                  "type": "object",
                  "additionalProperties": true
                }
              ]
            },
            "selected_specializations": {
              "type": "array",
              "items": {
                "type": "string"
              }
            },
            "coordination_requirements": {
              "type": "object",
              "additionalProperties": true
            },
            "director_inbox_submit_required": {
              "type": "boolean"
            },
            "parameters": {
              "type": "object",
              "additionalProperties": true
            },
            "allowed_tools": {
              "type": "array",
              "items": {
                "type": "string"
              }
            },
            "allowed_templates": {
              "type": "array",
              "items": {
                "type": "string"
              }
            },
            "selected_sources": {
              "type": "array",
              "items": {
                "type": "string"
              }
            },
            "obligations": {
              "type": "object",
              "additionalProperties": true
            },
            "egress": {
              "type": "object",
              "required": [
                "policy_id",
                "recipient",
                "purpose",
                "policy_checksum",
                "detector_checksum",
                "minimum_enforcement",
                "limits"
              ],
              "properties": {
                "policy_id": {
                  "type": "string",
                  "pattern": "^[a-z][a-z0-9-]{0,63}$"
                },
                "recipient": {
                  "type": "string",
                  "pattern": "^[a-z][a-z0-9-]{0,63}$"
                },
                "purpose": {
                  "type": "string",
                  "pattern": "^[a-z][a-z0-9-]{0,63}$"
                },
                "policy_checksum": {
                  "type": "string",
                  "pattern": "^sha256:[a-f0-9]{64}$"
                },
                "detector_checksum": {
                  "type": "string",
                  "pattern": "^sha256:[a-f0-9]{64}$"
                },
                "minimum_enforcement": {
                  "const": "mediated_session"
                },
                "limits": {
                  "type": "object",
                  "required": [
                    "unit_bytes",
                    "envelope_bytes",
                    "attempt_bytes",
                    "disclosures",
                    "json_depth",
                    "classification_ms",
                    "token_seconds"
                  ],
                  "properties": {
                    "unit_bytes": {
                      "type": "integer",
                      "minimum": 1,
                      "maximum": 1048576
                    },
                    "envelope_bytes": {
                      "type": "integer",
                      "minimum": 1,
                      "maximum": 4194304
                    },
                    "attempt_bytes": {
                      "type": "integer",
                      "minimum": 1,
                      "maximum": 33554432
                    },
                    "disclosures": {
                      "type": "integer",
                      "minimum": 1,
                      "maximum": 128
                    },
                    "json_depth": {
                      "type": "integer",
                      "minimum": 1,
                      "maximum": 16
                    },
                    "classification_ms": {
                      "type": "integer",
                      "minimum": 1,
                      "maximum": 2000
                    },
                    "token_seconds": {
                      "type": "integer",
                      "minimum": 1,
                      "maximum": 30
                    }
                  },
                  "additionalProperties": false
                }
              },
              "additionalProperties": false
            },
            "egress_predecessor": {
              "type": "object",
              "required": [
                "assignment_id",
                "capsule_checksum"
              ],
              "properties": {
                "assignment_id": {
                  "type": "string",
                  "pattern": "^[a-z0-9][a-z0-9-]{0,159}$"
                },
                "capsule_checksum": {
                  "type": "string",
                  "pattern": "^sha256:[a-f0-9]{64}$"
                }
              },
              "additionalProperties": false
            }
          },
          "additionalProperties": false
        },
        "required_source": {
          "type": "object",
          "required": [
            "path",
            "status",
            "required"
          ],
          "properties": {
            "path": {
              "type": "string",
              "minLength": 1
            },
            "status": {
              "enum": [
                "available",
                "unavailable"
              ]
            },
            "required": {
              "type": "boolean"
            },
            "size": {
              "type": "integer",
              "minimum": 0
            },
            "checksum": {
              "type": "string",
              "pattern": "^sha256:[a-f0-9]{64}$"
            },
            "reason": {
              "type": "string",
              "minLength": 1
            }
          },
          "oneOf": [
            {
              "properties": {
                "status": {
                  "const": "available"
                }
              },
              "required": [
                "size",
                "checksum"
              ]
            },
            {
              "properties": {
                "status": {
                  "const": "unavailable"
                }
              },
              "required": [
                "reason"
              ]
            }
          ],
          "additionalProperties": false
        },
        "capability": {
          "type": "object",
          "required": [
            "id",
            "status",
            "provider",
            "severity"
          ],
          "properties": {
            "id": {
              "type": "string",
              "minLength": 1
            },
            "status": {
              "enum": [
                "available",
                "missing"
              ]
            },
            "provider": {
              "type": [
                "string",
                "null"
              ]
            },
            "severity": {
              "enum": [
                "fail",
                "warn",
                "info"
              ]
            }
          },
          "additionalProperties": false
        }
      },
      "oneOf": [
        {
          "properties": {
            "contract_version": {
              "const": 1
            },
            "identity": {},
            "assignment_intent": {
              "properties": {
                "objective": {},
                "execution_mode": {},
                "scope": {},
                "required_sources": {},
                "context_artifacts": {},
                "outputs": {},
                "workspace_access": {},
                "subagent_policy": {},
                "required_capabilities": {},
                "optional_capabilities": {},
                "process": {},
                "selected_specializations": {},
                "coordination_requirements": {},
                "director_inbox_submit_required": {},
                "parameters": {},
                "allowed_tools": {},
                "allowed_templates": {},
                "selected_sources": {},
                "obligations": {}
              },
              "additionalProperties": false
            },
            "assignment_intent_checksum": {},
            "snapshot": {},
            "process": {},
            "resources": {},
            "scope": {},
            "required_sources": {},
            "outputs": {},
            "capabilities": {},
            "workspace_access": {},
            "parameters": {},
            "coordination": {},
            "worker_may_rebuild_context": {},
            "source_limits": {},
            "readiness": {},
            "contract_checksum": {}
          },
          "additionalProperties": false
        },
        {
          "required": [
            "egress"
          ],
          "properties": {
            "contract_version": {
              "const": 2
            },
            "assignment_intent": {
              "required": [
                "egress"
              ]
            }
          }
        }
      ]
    },
    "resource_bindings": {
      "type": "object",
      "required": [
        "schema_version",
        "resources",
        "status"
      ],
      "properties": {
        "schema_version": {
          "const": 1
        },
        "status": {
          "enum": [
            "available",
            "unavailable"
          ]
        },
        "reason": {
          "type": "string"
        },
        "limits": {
          "type": "object",
          "additionalProperties": {
            "type": "integer",
            "minimum": 1
          }
        },
        "resources": {
          "type": "array",
          "maxItems": 64,
          "items": {
            "$ref": "#/$defs/resource_bindings/$defs/resource"
          }
        }
      },
      "additionalProperties": false,
      "$defs": {
        "digest": {
          "type": "string",
          "pattern": "^sha256:[a-f0-9]{64}$"
        },
        "file": {
          "type": "object",
          "required": [
            "relative_path",
            "size",
            "sha256"
          ],
          "properties": {
            "relative_path": {
              "type": "string",
              "minLength": 1
            },
            "size": {
              "type": "integer",
              "minimum": 0
            },
            "sha256": {
              "$ref": "#/$defs/resource_bindings/$defs/digest"
            }
          },
          "additionalProperties": false
        },
        "resource": {
          "type": "object",
          "required": [
            "id",
            "status"
          ],
          "properties": {
            "id": {
              "type": "string",
              "minLength": 1
            },
            "status": {
              "enum": [
                "available",
                "unavailable"
              ]
            },
            "reason": {
              "type": "string",
              "minLength": 1
            },
            "generation": {
              "type": "string",
              "minLength": 1
            },
            "material_kind": {
              "enum": [
                "metadata",
                "fulltext",
                "none"
              ]
            },
            "metadata_fingerprint": {
              "$ref": "#/$defs/resource_bindings/$defs/digest"
            },
            "material_fingerprint": {
              "$ref": "#/$defs/resource_bindings/$defs/digest"
            },
            "reference": {
              "type": "object"
            },
            "indexing": {
              "type": "object"
            },
            "manifest": {
              "type": "array",
              "maxItems": 256,
              "items": {
                "$ref": "#/$defs/resource_bindings/$defs/file"
              }
            }
          },
          "oneOf": [
            {
              "properties": {
                "status": {
                  "const": "available"
                }
              },
              "required": [
                "generation",
                "material_kind",
                "metadata_fingerprint",
                "material_fingerprint",
                "reference",
                "indexing",
                "manifest"
              ]
            },
            {
              "properties": {
                "status": {
                  "const": "unavailable"
                }
              },
              "required": [
                "reason"
              ]
            }
          ],
          "additionalProperties": false
        }
      }
    },
    "id": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
    },
    "context_artifact": {
      "type": [
        "object",
        "string"
      ],
      "properties": {
        "path": {
          "type": "string"
        },
        "role": {
          "type": "string"
        },
        "required": {
          "type": "boolean"
        },
        "mutable_by_worker": {
          "type": "boolean"
        },
        "checksum": {
          "type": "string"
        }
      },
      "additionalProperties": true
    },
    "ownership": {
      "type": "object",
      "properties": {
        "owner_id": {
          "type": "string"
        },
        "owner_label": {
          "type": "string"
        },
        "role": {
          "type": "string"
        },
        "writer": {
          "type": "boolean"
        },
        "owned_files": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "owned_globs": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      },
      "additionalProperties": true
    },
    "required_output": {
      "type": [
        "object",
        "string"
      ],
      "properties": {
        "id": {
          "type": "string"
        },
        "type": {
          "type": "string"
        },
        "required": {
          "type": "boolean"
        }
      },
      "additionalProperties": true
    }
  },
  "additionalProperties": true
}
"""
_SEMANTIC_SCHEMA_SHA256 = (
    "74b049ed7508753bf724ccef2f9fb45ba6d1e8adf2648a60ac10a2b6d1193349"
)
if (
    hashlib.sha256(_SEMANTIC_SCHEMA_JSON.encode("utf-8")).hexdigest()
    != _SEMANTIC_SCHEMA_SHA256
):
    raise CompactError("unsupported_semantic_schema")
# Parse the exact reviewed schema once; recursively freeze every container.
# Schema expansion requires explicit versioned review of the evaluator subset.
_SEMANTIC_SCHEMA = _freeze(json.loads(_SEMANTIC_SCHEMA_JSON))
