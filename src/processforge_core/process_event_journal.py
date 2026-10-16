"""Durable process-event append with a bounded index of verified current bytes."""
from __future__ import annotations

from collections.abc import Callable
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
from types import FunctionType
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


@dataclass(frozen=True)
class _JournalIndex:
    digest: bytes
    size: int
    reader: Callable[[dict[str, Any]], str]
    ids: frozenset[str]
    strings_bytes: int
    parser_policy: _ParserPolicy


class ProcessEventJournal:
    """Keep only facts proved by an ordered scan of an exact journal byte string.

    The single private index retains at most ``max_index_bytes`` of ID strings
    and set storage. Every lookup reads and hashes the current file under the
    caller's existing cross-process writer guard. It grants no access and is
    never persisted. The canonical PF ID reader must be stable for truthy IDs;
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
            # A suppressed parse error disables indexing below. Reusing only
            # completely parsed bodies avoids trusting error constructors or
            # their descriptors, which can change without changing identity.
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
        return (left is not None and right is not None and left[1:] == right[1:]
                and len(left[0]) == len(right[0])
                and all(a is b for a, b in zip(left[0], right[0])))

    def _cached(self, digest: bytes, size: int, reader: Callable[[dict[str, Any]], str], parser_policy: _ParserPolicy | None) -> _JournalIndex | None:
        with self._index_lock:
            index = self._index
            if (index is not None and index.digest == digest and index.size == size
                    and index.reader is reader and self._same_policy(index.parser_policy, parser_policy)):
                return index
        return None

    def _within_bound(self, ids: set[str] | frozenset[str], strings_bytes: int) -> bool:
        return sys.getsizeof(ids) + strings_bytes <= self.max_index_bytes

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
        record = (json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        with writer_guard(path):
            raw = path.read_bytes() if path.is_file() else b""
            size = len(raw)
            clean_boundary = not raw or raw.endswith(b"\n")
            try:
                digest = hashlib.sha256(raw)
                parser_policy = self._parser_policy()
                cached = self._cached(digest.digest(), size, event_id_value, parser_policy)
            except Exception:
                digest, parser_policy, cached = None, None, None
            ids: set[str] | frozenset[str] | None
            strings_bytes = 0
            if cached is not None:
                exists = event_id in cached.ids
                ids, strings_bytes = cached.ids, cached.strings_bytes
                del raw
            else:
                self._replace_index(None)
                exists = False
                ids = None
                if self.max_index_bytes > 0 and digest is not None and parser_policy is not None:
                    try:
                        ids = set()
                    except MemoryError:
                        pass
                text = raw.decode("utf-8", errors="replace")
                del raw
                for line in text.splitlines():
                    try:
                        existing = json.loads(line)
                    except json.JSONDecodeError:
                        ids = None
                        continue
                    if not isinstance(existing, dict):
                        continue
                    existing_id = event_id_value(existing)
                    if existing_id == event_id:
                        exists = True
                        # The old algorithm stops here, including before later
                        # non-JSONDecodeError failures. A partial scan is no index.
                        ids = None
                        break
                    if ids is not None:
                        if not (existing.get("event_id") or existing.get("id")):
                            ids = None
                        elif existing_id not in ids:
                            try:
                                ids.add(existing_id)
                                strings_bytes += sys.getsizeof(existing_id)
                                if not self._within_bound(ids, strings_bytes):
                                    ids = None
                            except Exception:
                                ids = None
                del text

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
                if (ids is None or digest is None or parser_policy is None or not clean_boundary
                        or not self._same_policy(parser_policy, self._parser_policy())):
                    return
                if not exists:
                    ids = set(ids)
                    for line in record.decode("utf-8", errors="replace").splitlines():
                        try:
                            appended = json.loads(line)
                        except json.JSONDecodeError:
                            return
                        if isinstance(appended, dict):
                            if not (appended.get("event_id") or appended.get("id")):
                                return
                            appended_id = event_id_value(appended)
                            if appended_id not in ids:
                                ids.add(appended_id)
                                strings_bytes += sys.getsizeof(appended_id)
                    digest.update(record)
                    size += len(record)
                frozen_ids = frozenset(ids)
                if self._within_bound(frozen_ids, strings_bytes):
                    self._replace_index(_JournalIndex(digest.digest(), size, event_id_value, frozen_ids, strings_bytes, parser_policy))
            except Exception:
                self._replace_index(None)
