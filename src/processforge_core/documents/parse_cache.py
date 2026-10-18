"""Bounded reuse of safe YAML values, keyed by content rather than file metadata."""
from __future__ import annotations

from collections import OrderedDict
import copy
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import re
import sys
import threading
from types import BuiltinFunctionType, FunctionType
from typing import Any, Callable


@dataclass(frozen=True)
class _Entry:
    value: Any
    weight: int


class YamlParseCache:
    def __init__(self, *, max_bytes: int = 64 * 1024 * 1024,
                 max_entries: int = 4096, max_entry_bytes: int = 2 * 1024 * 1024) -> None:
        self.max_bytes = max_bytes
        self.max_entries = max_entries
        self.max_entry_bytes = max_entry_bytes
        self._lock = threading.RLock()
        self._entries: OrderedDict[tuple[Any, ...], _Entry] = OrderedDict()
        self._bytes = self._hits = self._parses = self._evictions = self._bypasses = 0

    @staticmethod
    def policy(loader: type, parser: Callable[..., Any]) -> tuple[Any, ...] | None:
        # Extensions can supply stateful constructors. Keep their original calls
        # rather than assuming every safe tag is a deterministic cached function.
        try:
            if not loader.__module__.startswith("yaml.") or parser.__module__ != "yaml":
                return None
            constructors = (loader.yaml_constructors, loader.yaml_multi_constructors)
            if any(not getattr(function, "__module__", "").startswith("yaml.")
                   for rules in constructors for function in rules.values()):
                return None
            if any(type(pattern) is not re.Pattern
                   for rules in loader.yaml_implicit_resolvers.values() for _, pattern in rules):
                return None
            rules = tuple(tuple((key, tuple(value) if isinstance(value, list) else value)
                                for key, value in getattr(loader, name).items())
                          for name in ("yaml_constructors", "yaml_multi_constructors",
                                       "yaml_implicit_resolvers", "yaml_path_resolvers"))
            policy = (loader, parser, rules)
            hash(policy)
            return policy
        except (AttributeError, TypeError, RuntimeError):
            return None

    @staticmethod
    def _content(text: str) -> tuple[int, bytes]:
        digest = hashlib.sha256()
        size = 0
        for start in range(0, len(text), 65536):
            block = text[start:start + 65536].encode("utf-8", errors="surrogatepass")
            size += len(block)
            digest.update(block)
        return size, digest.digest()

    @staticmethod
    def _select(value: Any, fields: tuple[str, ...] | None) -> Any:
        if fields is None:
            return value
        return {key: value[key] for key in fields if key in value} if isinstance(value, dict) else {}

    @staticmethod
    def _weight(value: Any, limit: int, *, validate: bool) -> int | None:
        pending, seen, size = [value], set(), 0
        scalar_types = (str, bytes, int, float, bool, type(None), date, datetime)
        container_types = (dict, list, tuple, set, frozenset)
        policy_types = (type, FunctionType, BuiltinFunctionType, re.Pattern)
        while pending:
            item = pending.pop()
            if id(item) in seen:
                continue
            seen.add(id(item))
            kind = type(item)
            allowed = scalar_types + container_types + (() if validate else policy_types)
            if kind not in allowed:
                return None
            size += sys.getsizeof(item)
            if size > limit:
                return None
            if kind is dict:
                pending.extend(item.keys())
                pending.extend(item.values())
            elif kind in (list, tuple, set, frozenset):
                pending.extend(item)
        return size

    def _remember(self, key: tuple[Any, ...], value: Any) -> None:
        limit = min(self.max_bytes, self.max_entry_bytes)
        key_weight = self._weight(key, limit, validate=False)
        value_weight = self._weight(value, limit, validate=True)
        if (self.max_entries <= 0 or key_weight is None or value_weight is None
                or key_weight + value_weight > limit):
            with self._lock:
                self._bypasses += 1
            return
        try:
            snapshot = copy.deepcopy(value)
        except (MemoryError, RecursionError):
            # An optional optimization must not reject an otherwise valid parse.
            with self._lock:
                self._bypasses += 1
            return
        actual = self._weight(snapshot, limit - key_weight, validate=True)
        if actual is None:
            with self._lock:
                self._bypasses += 1
            return
        weight = key_weight + actual
        with self._lock:
            if key in self._entries:
                self._entries.move_to_end(key)
                return
            while self._entries and (len(self._entries) >= self.max_entries
                                     or self._bytes + weight > self.max_bytes):
                _, entry = self._entries.popitem(last=False)
                self._bytes -= entry.weight
                self._evictions += 1
            self._entries[key] = _Entry(snapshot, weight)
            self._bytes += weight

    def load(self, text: str, loader: type, parser: Callable[..., Any], *,
             policy: tuple[Any, ...] | None, fields: tuple[str, ...] | None = None) -> tuple[Any, bool]:
        key = None
        entry = None
        selected_from_full = False
        if policy is not None and isinstance(text, str):
            size, digest = self._content(text)
            key = (policy, size, digest, fields)
            candidate = key
            with self._lock:
                entry = self._entries.get(candidate)
                if entry is None and fields is not None:
                    candidate = (policy, size, digest, None)
                    entry = self._entries.get(candidate)
                    selected_from_full = entry is not None
                if entry is not None:
                    self._entries.move_to_end(candidate)
            if entry is not None:
                try:
                    value = copy.deepcopy(self._select(entry.value, fields) if selected_from_full else entry.value)
                except (MemoryError, RecursionError):
                    with self._lock:
                        removed = self._entries.pop(candidate, None)
                        if removed is not None:
                            self._bytes -= removed.weight
                else:
                    with self._lock:
                        self._hits += 1
                    if selected_from_full:
                        self._remember(key, value)
                    return value, True
        with self._lock:
            self._parses += 1
            if key is None:
                self._bypasses += 1
        value = self._select(parser(text, Loader=loader), fields)
        if key is not None and self.policy(loader, parser) == policy:
            self._remember(key, value)
        return value, False

    def info(self) -> dict[str, int]:
        with self._lock:
            return {"entries": len(self._entries), "bytes": self._bytes,
                    "hits": self._hits, "parses": self._parses,
                    "evictions": self._evictions, "bypasses": self._bypasses}

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._bytes = self._hits = self._parses = self._evictions = self._bypasses = 0
