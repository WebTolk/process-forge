"""Safe content-based parsing reuse, with an additional synchronous request scope."""
from __future__ import annotations

import contextvars
import copy
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from .. import diagnostics
from ..documents.parse_cache import YamlParseCache

MAX_DOCUMENT_BYTES = 512 * 1024
MAX_CACHE_BYTES = 8 * 1024 * 1024
MAX_CACHE_ENTRIES = 1024
_PARSE_CACHE = YamlParseCache()


@dataclass
class RequestScope:
    documents: dict[tuple[Any, ...], Any] = field(default_factory=dict)
    bytes: int = 0
    loads: int = 0
    parses: int = 0
    hits: int = 0


_CURRENT: contextvars.ContextVar[RequestScope | None] = contextvars.ContextVar("pf_request_scope", default=None)
F = TypeVar("F", bound=Callable[..., Any])


class _ScopeContext:
    def __init__(self) -> None:
        self.token: contextvars.Token | None = None

    def __enter__(self) -> RequestScope:
        current = _CURRENT.get()
        if current is None:
            current = RequestScope()
            self.token = _CURRENT.set(current)
        return current

    def __exit__(self, *_exception: Any) -> None:
        if self.token is not None:
            _CURRENT.reset(self.token)


def request_scope() -> _ScopeContext:
    return _ScopeContext()


def scoped_request(function: F) -> F:
    @wraps(function)
    def scoped(*args: Any, **kwargs: Any) -> Any:
        outermost = _CURRENT.get() is None
        with request_scope() as scope:
            trace = diagnostics.span("work.request", {"operation": function.__name__})
            trace.__enter__()
            try:
                return function(*args, **kwargs)
            finally:
                # Generator context managers rewrite frozen exception tracebacks.
                # The optional span needs only completion, not exception injection.
                trace.__exit__(None, None, None)
                if outermost:
                    diagnostics.emit("debug", "work.request.yaml", {
                        "operation": function.__name__, "loads": scope.loads,
                        "parses": scope.parses, "hits": scope.hits,
                        "entries": len(scope.documents), "bytes": scope.bytes,
                    })
    return cast(F, scoped)


def safe_load(text: str) -> Any:
    return _load(text, None)


def safe_load_fields(text: str, fields: tuple[str, ...]) -> dict[str, Any]:
    return _load(text, fields)


def _load(text: str, fields: tuple[str, ...] | None) -> Any:
    import yaml

    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    policy = _PARSE_CACHE.policy(loader, yaml.load)
    scope = _CURRENT.get()
    key = (policy, fields, text)
    if scope is not None:
        scope.loads += 1
    if scope is not None and policy is not None and key in scope.documents:
        scope.hits += 1
        return copy.deepcopy(scope.documents[key])
    if scope is not None:
        scope.parses += 1
    value, reused = _PARSE_CACHE.load(text, loader, yaml.load, policy=policy, fields=fields)
    if scope is None:
        return value
    if reused:
        scope.parses -= 1
        scope.hits += 1
    # Retain an independent snapshot; callers may mutate even the first result.
    if (policy is not None and _PARSE_CACHE.policy(loader, yaml.load) == policy
            and len(text) <= MAX_DOCUMENT_BYTES):
        size = len(text.encode("utf-8"))
        if (size <= MAX_DOCUMENT_BYTES and len(scope.documents) < MAX_CACHE_ENTRIES
                and scope.bytes + size <= MAX_CACHE_BYTES):
            scope.documents[key] = copy.deepcopy(value)
            scope.bytes += size
    return value
