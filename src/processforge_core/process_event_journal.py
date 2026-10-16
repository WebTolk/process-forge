"""Durable process-event append with a bounded index of verified current bytes."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
import hashlib
import json
import math
import os
import re
from pathlib import Path
import sys
from threading import Lock
from types import FunctionType, MappingProxyType
from typing import Any

_ParserPolicy = tuple[tuple[object, ...], int | None, int]
def _optional_parser_definitions() -> tuple[object, ...]:
    """Capture optional plain definitions without invoking class descriptors."""
    try:
        loads = vars(json).get("loads")
        decoder = vars(json).get("JSONDecoder")
        decode = vars(decoder).get("decode") if type(decoder) is type else None
        raw_decode = vars(decoder).get("raw_decode") if type(decoder) is type else None
        functions = (loads, decode, raw_decode)
        if any(type(function) is not FunctionType for function in functions):
            return (None,) * 7
        return (loads, loads.__code__, decoder, decode, raw_decode,
                decode.__code__, raw_decode.__code__)
    except Exception:
        return (None,) * 7


(_JSON_LOADS, _JSON_LOADS_CODE, _JSON_DECODER, _JSON_DECODE,
 _JSON_RAW_DECODE, _JSON_DECODE_CODE, _JSON_RAW_DECODE_CODE) = _optional_parser_definitions()


def _optional_serializer_definitions() -> tuple[object, ...] | None:
    """Recognize the ordinary C-backed encoder without calling custom code."""
    try:
        dumps = vars(json).get("dumps")
        encoder = vars(json).get("JSONEncoder")
        module = vars(json.encoder)
        if type(dumps) is not FunctionType or type(encoder) is not type:
            return None
        methods = tuple(vars(encoder).get(name) for name in ("__init__", "encode", "iterencode", "default"))
        if any(type(method) is not FunctionType for method in methods):
            return None
        if (dumps.__module__ != "json" or dumps.__globals__ is not vars(json)
                or dumps.__code__.co_filename != json.__file__
                or encoder.__module__ != "json.encoder"
                or any(method.__globals__ is not module or method.__code__.co_filename != json.encoder.__file__ for method in methods)):
            return None
        defaults = {"skipkeys": False, "ensure_ascii": True, "check_circular": True,
                    "allow_nan": True, "sort_keys": False, "indent": None,
                    "separators": None, "default": None}
        for function, expected in ((dumps, dict(defaults, cls=None)), (methods[0], defaults)):
            actual = function.__kwdefaults__
            if type(actual) is not dict or len(actual) != len(expected) or any(actual.get(key) is not value for key, value in expected.items()):
                return None
        attributes = vars(encoder)
        if (type(attributes.get("item_separator")) is not str
                or type(attributes.get("key_separator")) is not str
                or attributes.get("item_separator") != ", " or attributes.get("key_separator") != ": "
                or any(name in attributes for name in ("__new__", "__getattribute__", "__setattr__"))):
            return None
        make_encoder = module.get("c_make_encoder")
        encode_string = module.get("encode_basestring")
        if (type(make_encoder) is not type or make_encoder.__module__ != "_json"
                or type(encode_string) is not type(len) or encode_string.__module__ != "_json"):
            return None
        return (dumps, dumps.__code__, encoder, *methods,
                *(method.__code__ for method in methods), make_encoder, encode_string)
    except Exception:
        return None


_RECORD_SERIALIZER_DEFINITIONS = _optional_serializer_definitions()


@dataclass(frozen=True, slots=True)
class _JournalIndex:
    digest: bytes
    size: int
    reader: Callable[[dict[str, Any]], str]
    positions: Mapping[str, int]
    bad_rows: tuple[tuple[int, str], ...]
    line_count: int
    value_bytes: int
    parser_policy: _ParserPolicy
    parsing_depth: int


class ProcessEventJournal:
    """Keep only facts proved by an ordered scan of an exact journal byte string.

    The single private index bounds ID positions, failed rows and their storage.
    Every lookup reads and hashes current bytes; append uses the caller's
    existing cross-process writer guard. It grants no access and is never
    persisted. The canonical PF ID reader must be stable for truthy IDs;
    rows that would use its random missing-ID fallback disable indexing.
    """

    def __init__(self, *, max_index_bytes: int = 16 * 1024 * 1024) -> None:
        self.max_index_bytes = max_index_bytes
        self._index: _JournalIndex | None = None
        self._index_lock = Lock()

    def _replace_index(self, index: _JournalIndex | None) -> None:
        with self._index_lock:
            self._index = index

    @staticmethod
    def _parser_policy() -> _ParserPolicy | None:
        try:
            decoder = getattr(json, "_default_decoder", None)
            # Identity is insufficient for a configured callback with mutable
            # state. Index only the ordinary stdlib fast path and builtin
            # scalar handlers; custom/unknown behavior keeps the full scan.
            if (_JSON_LOADS is None or json.loads is not _JSON_LOADS or _JSON_LOADS.__code__ is not _JSON_LOADS_CODE
                    or _JSON_LOADS.__module__ != "json" or _JSON_LOADS.__globals__ is not vars(json)
                    or _JSON_LOADS_CODE.co_filename != json.__file__
                    or json.JSONDecoder is not _JSON_DECODER or type(decoder) is not _JSON_DECODER
                    or vars(_JSON_DECODER).get("decode") is not _JSON_DECODE or _JSON_DECODE.__code__ is not _JSON_DECODE_CODE
                    or vars(_JSON_DECODER).get("raw_decode") is not _JSON_RAW_DECODE or _JSON_RAW_DECODE.__code__ is not _JSON_RAW_DECODE_CODE):
                return None
            state = vars(decoder)
            # Bad rows are replayed below. Do not inspect error constructors
            # or their descriptors, which can change without changing identity.
            if any(vars(json.decoder).get(key, value) is not value for key, value in (
                    ("ValueError", ValueError), ("StopIteration", StopIteration), ("len", len))):
                return None
            if any(vars(json).get(key, value) is not value for key, value in (
                    ("str", str), ("isinstance", isinstance))):
                return None
            defaults = _JSON_LOADS.__kwdefaults__
            expected_defaults = ("cls", "object_hook", "parse_float", "parse_int", "parse_constant", "object_pairs_hook")
            if (not isinstance(defaults, dict) or len(defaults) != len(expected_defaults)
                    or any(key not in defaults or defaults[key] is not None for key in expected_defaults)
                    or "decode" in state or "raw_decode" in state):
                return None
            scanner = state.get("scan_once")
            if type(scanner) is not getattr(json.scanner, "c_make_scanner", None):
                return None
            if (state.get("parse_int") is not int or state.get("parse_float") is not float
                    or state.get("object_hook") is not None or state.get("object_pairs_hook") is not None
                    or state.get("strict") is not True):
                return None
            for key in ("parse_int", "parse_float", "parse_constant", "object_hook", "object_pairs_hook", "strict"):
                if getattr(scanner, key, None) is not state.get(key):
                    return None
            constants = json.decoder._CONSTANTS
            constant_reader = state.get("parse_constant")
            if (type(constants) is not dict or len(constants) != 3
                    or type(constant_reader) is not type({}.__getitem__)
                    or constant_reader.__name__ != "__getitem__" or constant_reader.__self__ is not constants
                    or type(constants.get("NaN")) is not float or not math.isnan(constants["NaN"])
                    or type(constants.get("Infinity")) is not float or constants["Infinity"] != math.inf
                    or type(constants.get("-Infinity")) is not float or constants["-Infinity"] != -math.inf):
                return None
            whitespace_defaults = _JSON_DECODE.__defaults__
            raw_defaults = _JSON_RAW_DECODE.__defaults__
            if (not isinstance(whitespace_defaults, tuple) or len(whitespace_defaults) != 1
                    or type(json.decoder.WHITESPACE) is not re.Pattern
                    or type(whitespace_defaults[0]) is not type(json.decoder.WHITESPACE.match)
                    or getattr(whitespace_defaults[0], "__name__", None) != "match"
                    or getattr(whitespace_defaults[0], "__self__", None) is not json.decoder.WHITESPACE
                    or not isinstance(raw_defaults, tuple) or len(raw_defaults) != 1
                    or type(raw_defaults[0]) is not int or raw_defaults[0] != 0):
                return None
            references = (
                json.loads, decoder, json.JSONDecoder.decode, json.JSONDecoder.raw_decode,
                *whitespace_defaults, *raw_defaults,
                *(state.get(name) for name in (
                    "decode", "raw_decode", "scan_once", "parse_object", "parse_array",
                    "parse_string", "parse_float", "parse_int", "parse_constant",
                    "object_hook", "object_pairs_hook", "strict",
                )),
            )
            integer_limit_reader = getattr(sys, "get_int_max_str_digits", None)
            integer_limit = integer_limit_reader() if integer_limit_reader is not None else None
            return references, integer_limit, sys.getrecursionlimit()
        except Exception:
            return None

    @staticmethod
    def _same_policy(left: _ParserPolicy | None, right: _ParserPolicy | None) -> bool:
        try:
            return (left is not None and right is not None and left[1:] == right[1:]
                    and len(left[0]) == len(right[0])
                    and all(a is b for a, b in zip(left[0], right[0])))
        except Exception:
            return False

    @staticmethod
    def _ordinary_record_serialization() -> bool:
        try:
            current = _optional_serializer_definitions()
            return (current is not None and _RECORD_SERIALIZER_DEFINITIONS is not None
                    and len(current) == len(_RECORD_SERIALIZER_DEFINITIONS)
                    and all(a is b for a, b in zip(current, _RECORD_SERIALIZER_DEFINITIONS)))
        except Exception:
            return False

    def _cached(self, digest: bytes, size: int, reader: Callable[[dict[str, Any]], str], parser_policy: _ParserPolicy | None) -> _JournalIndex | None:
        with self._index_lock:
            index = self._index
            if (index is not None and index.digest == digest and index.size == size
                    and index.reader is reader and self._same_policy(index.parser_policy, parser_policy)):
                return index
        return None

    def _within_bound(self, positions: Mapping[str, int], bad_rows: list[tuple[int, str]] | tuple[tuple[int, str], ...], value_bytes: int) -> bool:
        # Leave space for the immutable index, proxy, digest and policy tuples.
        return sys.getsizeof(positions) + sys.getsizeof(bad_rows) + value_bytes + 2048 <= self.max_index_bytes

    @staticmethod
    def _allocate_metadata() -> tuple[dict[str, int], list[tuple[int, str]]]:
        return {}, []

    @staticmethod
    def _parsing_depth() -> int:
        frame = sys._getframe(1)
        depth = 0
        while frame is not None:
            depth += 1
            frame = frame.f_back
        return depth

    @staticmethod
    def _record_id(line: str, reader: Callable[[dict[str, Any]], str]) -> tuple[str | None, int]:
        # Keep new-record parsing/ID construction at the same frame depth as
        # lookup parsing. A deeper future caller cannot reuse shallower facts.
        depth = ProcessEventJournal._parsing_depth()
        item = json.loads(line)
        if not isinstance(item, dict) or not (item.get("event_id") or item.get("id")):
            return None, depth
        value = reader(item)
        return (value if type(value) is str else None), depth

    def _publish(self, digest: bytes, size: int, reader: Callable[[dict[str, Any]], str], positions: dict[str, int], bad_rows: list[tuple[int, str]], line_count: int, value_bytes: int, policy: _ParserPolicy, parsing_depth: int) -> None:
        try:
            if self._within_bound(positions, bad_rows, value_bytes):
                self._replace_index(_JournalIndex(digest, size, reader, MappingProxyType(positions), tuple(bad_rows), line_count, value_bytes, policy, parsing_depth))
        except Exception:
            self._replace_index(None)

    @staticmethod
    def _scan_suffix(raw: bytes, start: int, event_id: str, reader: Callable[[dict[str, Any]], str], *, skip_blank: bool) -> bool:
        # The current replay row was already consumed. Starting after it avoids
        # calling a stateful constructor twice or reparsing an earlier prefix
        # under a policy that the constructor has just changed.
        for line in raw.decode("utf-8", errors="replace").splitlines()[start:]:
            if skip_blank and not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and reader(item) == event_id:
                return True
        return False

    def _lookup(self, raw: bytes, event_id: str, reader: Callable[[dict[str, Any]], str], *, skip_blank: bool) -> bool:
        depth = 0
        try:
            digest = hashlib.sha256(raw).digest()
            policy = self._parser_policy()
            depth = self._parsing_depth()
            cached = self._cached(digest, len(raw), reader, policy) if type(event_id) is str else None
            if cached is not None and depth > cached.parsing_depth:
                cached = None
        except Exception:
            digest, policy, cached = None, None, None
        if cached is not None:
            stop = cached.positions.get(event_id, cached.line_count)
            for ordinal, line in cached.bad_rows:
                if ordinal >= stop:
                    break
                if skip_blank and not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    if self._same_policy(policy, self._parser_policy()):
                        continue
                else:
                    # Unknown changed behavior: consume this row once, then
                    # use the mandatory original scan for the remaining rows.
                    self._replace_index(None)
                    if isinstance(item, dict) and reader(item) == event_id:
                        return True
                self._replace_index(None)
                return self._scan_suffix(raw, ordinal + 1, event_id, reader, skip_blank=skip_blank)
            return event_id in cached.positions

        self._replace_index(None)
        positions, bad_rows, value_bytes = None, [], 0
        if self.max_index_bytes > 0 and digest is not None and policy is not None and type(event_id) is str:
            try:
                positions, bad_rows = self._allocate_metadata()
            except Exception:
                pass
        lines = raw.decode("utf-8", errors="replace").splitlines()
        for ordinal, line in enumerate(lines):
            ignored = skip_blank and not line.strip()
            if not ignored:
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    ignored = True
                    if positions is not None and not self._same_policy(policy, self._parser_policy()):
                        positions = None
                        bad_rows = []
            if ignored:
                if positions is not None:
                    try:
                        row = (ordinal, line)
                        bad_rows.append(row)
                        value_bytes += sys.getsizeof(row) + sys.getsizeof(ordinal) + sys.getsizeof(line)
                        if not self._within_bound(positions, bad_rows, value_bytes):
                            positions, bad_rows = None, []
                    except Exception:
                        positions, bad_rows = None, []
                continue
            if not isinstance(item, dict):
                continue
            existing_id = reader(item)
            if existing_id == event_id:
                return True  # No partial index after a cold early duplicate.
            if positions is not None:
                if not (item.get("event_id") or item.get("id")) or type(existing_id) is not str:
                    positions, bad_rows = None, []
                else:
                    try:
                        if existing_id not in positions:
                            positions[existing_id] = ordinal
                            value_bytes += sys.getsizeof(existing_id) + sys.getsizeof(ordinal)
                            if not self._within_bound(positions, bad_rows, value_bytes):
                                positions, bad_rows = None, []
                    except Exception:
                        positions, bad_rows = None, []
        if (positions is not None and digest is not None and policy is not None
                and (not raw or raw.endswith(b"\n")) and self._same_policy(policy, self._parser_policy())):
            self._publish(digest, len(raw), reader, positions, bad_rows, len(lines), value_bytes, policy, depth)
        return False

    def contains(self, path: Path, event_id: str, *, event_id_value: Callable[[dict[str, Any]], str]) -> bool:
        """Read current bytes without any filesystem mutation or writer lock."""
        if not path.is_file():
            return False
        return self._lookup(path.read_bytes(), event_id, event_id_value, skip_blank=True)

    def append(
        self,
        path: Path,
        event: dict[str, Any],
        *,
        writer_guard: Callable[[Path], AbstractContextManager[Any]],
        event_id_value: Callable[[dict[str, Any]], str],
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        event_id = event_id_value(event)
        ordinary_serialization = self._ordinary_record_serialization()
        record = (json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        ordinary_serialization = ordinary_serialization and self._ordinary_record_serialization()
        with writer_guard(path):
            raw = path.read_bytes() if path.is_file() else b""
            size = len(raw)
            clean_boundary = not raw or raw.endswith(b"\n")
            exists = self._lookup(raw, event_id, event_id_value, skip_blank=False)
            try:
                digest = hashlib.sha256(raw)
                parser_policy = self._parser_policy()
                cached = self._cached(digest.digest(), size, event_id_value, parser_policy)
            except Exception:
                digest, parser_policy, cached = None, None, None
            del raw

            # A failed or partially durable write must never leave a trusted
            # prediction of its result in this instance.
            self._replace_index(None)
            with path.open("ab") as handle:
                if not exists:
                    handle.write(record)
                handle.flush()
                os.fsync(handle.fileno())

            # Index maintenance is optional and happens only after the original
            # mandatory durable operation. Any inability to retain it is a miss.
            try:
                if (cached is None or digest is None or parser_policy is None or not clean_boundary
                        or not self._same_policy(parser_policy, self._parser_policy())):
                    return
                positions = dict(cached.positions)
                bad_rows = list(cached.bad_rows)
                value_bytes = cached.value_bytes
                line_count = cached.line_count
                parsing_depth = cached.parsing_depth
                if not exists:
                    record_lines = record.decode("utf-8", errors="replace").splitlines()
                    if bad_rows and (not ordinary_serialization or len(record_lines) != 1):
                        return  # V5 did not parse unproved records after bad history.
                    for ordinal, line in enumerate(record_lines, start=line_count):
                        try:
                            appended_id, record_depth = self._record_id(line, event_id_value)
                        except json.JSONDecodeError:
                            return
                        if appended_id is None:
                            return
                        parsing_depth = min(parsing_depth, record_depth)
                        if appended_id not in positions:
                            positions[appended_id] = ordinal
                            value_bytes += sys.getsizeof(appended_id) + sys.getsizeof(ordinal)
                    line_count += len(record_lines)
                    digest.update(record)
                    size += len(record)
                self._publish(digest.digest(), size, event_id_value, positions, bad_rows, line_count, value_bytes, parser_policy, parsing_depth)
            except Exception:
                self._replace_index(None)
