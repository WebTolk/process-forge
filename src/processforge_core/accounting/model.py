"""Immutable accounting facts, provenance and bounded query values."""

from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

Quality = Literal["measured", "partial", "unknown"]
SourceStatus = Literal["available", "missing", "partial", "unsupported"]
METRICS = (
    "input_total",
    "output_total",
    "input_cache_read",
    "input_cache_write",
    "output_reasoning",
    "reported_total",
)


def identifier(value: str, name: str) -> None:
    """Reject empty, unbounded or control-bearing identifiers."""
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ValueError(f"invalid {name}")
    if any(ord(char) < 32 for char in value):
        raise ValueError(f"invalid {name}")


def nonnegative(value: int | None, name: str) -> None:
    """Validate nullable integer measurements without accepting bool."""
    if value is not None and (type(value) is not int or value < 0):
        raise ValueError(f"invalid {name}")


def utc(value: datetime, name: str) -> None:
    """Require an aware UTC timestamp without silently interpreting local time."""
    if not isinstance(value, datetime) or value.utcoffset() != timedelta(0):
        raise ValueError(f"{name} must be aware UTC")


@dataclass(frozen=True, kw_only=True)
class FactKey:
    """Canonical origin/source/occurrence independent of transport."""

    origin_id: str
    source_id: str
    record_id: str

    def __post_init__(self) -> None:
        for name in ("origin_id", "source_id", "record_id"):
            identifier(getattr(self, name), name)


@dataclass(frozen=True, kw_only=True)
class Attribution:
    """Proven binding; null project means quarantined, never a guessed project."""

    project_id: str | None
    agent_instance_id: str
    session_id: str | None = None
    run_id: str | None = None
    assignment_id: str | None = None
    attempt: int | None = None
    provider: str | None = None
    model: str | None = None

    def __post_init__(self) -> None:
        identifier(self.agent_instance_id, "agent_instance_id")
        for name in (
            "project_id",
            "session_id",
            "run_id",
            "assignment_id",
            "provider",
            "model",
        ):
            value = getattr(self, name)
            if value is not None:
                identifier(value, name)
        nonnegative(self.attempt, "attempt")
        if self.attempt is not None and (
            not 1 <= self.attempt <= 2**63 - 1 or self.assignment_id is None
        ):
            raise ValueError("attempt requires assignment and positive number")
        if self.project_id is None and any(
            value is not None
            for value in (self.run_id, self.assignment_id, self.attempt)
        ):
            raise ValueError("quarantine cannot have PF task binding")


@dataclass(frozen=True, kw_only=True)
class Provenance:
    """Private source location/hash and normalization version; never public DTO data."""

    source_ref: str
    source_hash: str
    adapter_version: str

    def __post_init__(self) -> None:
        for name in ("source_ref", "source_hash"):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value
                or len(value.encode("utf-8")) > 4096
            ):
                raise ValueError(f"invalid {name}")
        identifier(self.adapter_version, "adapter_version")


@dataclass(frozen=True, kw_only=True)
class TokenCounts:
    """Nullable absolute unit counters; cache and reasoning are inclusive subsets."""

    input_total: int | None = None
    output_total: int | None = None
    input_cache_read: int | None = None
    input_cache_write: int | None = None
    output_reasoning: int | None = None
    reported_total: int | None = None

    def __post_init__(self) -> None:
        for name in METRICS:
            nonnegative(getattr(self, name), name)
        cache = (self.input_cache_read, self.input_cache_write)
        if (
            self.input_total is not None
            and sum(v for v in cache if v is not None) > self.input_total
        ):
            raise ValueError("cache subsets exceed input")
        if (
            self.output_total is not None
            and self.output_reasoning is not None
            and self.output_reasoning > self.output_total
        ):
            raise ValueError("reasoning exceeds output")
        if self.reported_total is not None:
            known = sum(
                v for v in (self.input_total, self.output_total) if v is not None
            )
            if known > self.reported_total or (
                self.total is not None and self.total != self.reported_total
            ):
                raise ValueError("reported total contradicts counters")

    @property
    def total(self) -> int | None:
        """Return inclusive input plus output only when both are observed."""
        if self.input_total is None or self.output_total is None:
            return None
        return self.input_total + self.output_total


def _fact(revision: int, quality: Quality, valid: bool) -> None:
    nonnegative(revision, "revision")
    if type(revision) is not int or revision > 2**63 - 1:
        raise ValueError("revision exceeds SQLite integer")
    if quality not in ("measured", "partial", "unknown") or type(valid) is not bool:
        raise ValueError("invalid fact quality/validity")


@dataclass(frozen=True, kw_only=True)
class UsageRecord:
    """One absolute usage contribution, including partial/failed attempts."""

    key: FactKey
    revision: int
    attribution: Attribution
    occurred_at: datetime
    tokens: TokenCounts
    provenance: Provenance
    quality: Quality = "measured"
    valid: bool = True

    def __post_init__(self) -> None:
        _fact(self.revision, self.quality, self.valid)
        utc(self.occurred_at, "occurred_at")


@dataclass(frozen=True, kw_only=True)
class ActivityInterval:
    """Confirmed activity span; an unfinished interval never extends to query time."""

    key: FactKey
    revision: int
    attribution: Attribution
    start: datetime
    end: datetime | None
    elapsed_seconds: float | None
    provenance: Provenance
    quality: Quality = "measured"
    valid: bool = True

    def __post_init__(self) -> None:
        _fact(self.revision, self.quality, self.valid)
        utc(self.start, "start")
        elapsed = self.elapsed_seconds
        if elapsed is not None and (
            isinstance(elapsed, bool)
            or not isinstance(elapsed, (int, float))
            or not math.isfinite(elapsed)
            or elapsed < 0
        ):
            raise ValueError("invalid elapsed_seconds")
        if self.end is not None:
            utc(self.end, "end")

    @property
    def utc_span_seconds(self) -> float | None:
        """Return signed calendar distance, independently of monotonic duration."""
        return (self.end - self.start).total_seconds() if self.end is not None else None

    @property
    def clock_discrepancy_seconds(self) -> float | None:
        """Return monotonic minus calendar seconds when both were observed."""
        span = self.utc_span_seconds
        if self.elapsed_seconds is None or span is None:
            return None
        return self.elapsed_seconds - span

    @property
    def clock_quality(self) -> str:
        """Describe observed clock agreement without changing source quality."""
        span = self.utc_span_seconds
        if span is None:
            return "monotonic_only" if self.elapsed_seconds is not None else "unknown"
        if span < 0:
            return "reversed"
        discrepancy = self.clock_discrepancy_seconds
        if discrepancy is None:
            return "utc_only"
        return "aligned" if abs(discrepancy) <= 0.000001 else "discrepant"

    @property
    def confirmed_end(self) -> datetime | None:
        """Return an observed forward UTC end; monotonic time cannot supply one."""
        return self.end if self.end is not None and self.end >= self.start else None


@dataclass(frozen=True, kw_only=True)
class SourceCursor:
    """Bounded opaque replay position with an ordered checkpoint revision."""

    origin_id: str
    source_id: str
    position: str
    revision: int
    updated_at: datetime

    def __post_init__(self) -> None:
        identifier(self.origin_id, "origin_id")
        identifier(self.source_id, "source_id")
        _fact(self.revision, "measured", True)
        utc(self.updated_at, "updated_at")
        if (
            not isinstance(self.position, str)
            or len(self.position.encode("utf-8")) > 4096
        ):
            raise ValueError("cursor position exceeds bound")


@dataclass(frozen=True, kw_only=True)
class SourceCapability:
    """Project-specific source inventory and explicitly supported measurements."""

    origin_id: str
    source_id: str
    project_id: str
    adapter_version: str
    observed_at: datetime
    supported_metrics: tuple[str, ...] = ()
    status: SourceStatus = "available"

    def __post_init__(self) -> None:
        for name in ("origin_id", "source_id", "project_id", "adapter_version"):
            identifier(getattr(self, name), name)
        utc(self.observed_at, "observed_at")
        if self.status not in ("available", "missing", "partial", "unsupported"):
            raise ValueError("invalid source status")
        if not isinstance(self.supported_metrics, tuple) or len(
            set(self.supported_metrics)
        ) != len(self.supported_metrics):
            raise ValueError("supported_metrics must be a unique tuple")
        if any(name not in (*METRICS, "activity") for name in self.supported_metrics):
            raise ValueError("unsupported metric name")


@dataclass(frozen=True, kw_only=True)
class QueryFilter:
    """Half-open calendar window and explicit bounded pagination."""

    project_id: str | None = None
    assignment_id: str | None = None
    run_id: str | None = None
    attempt: int | None = None
    source_id: str | None = None
    model: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    limit: int = 100
    offset: int = 0

    def __post_init__(self) -> None:
        for name in ("project_id", "assignment_id", "run_id", "source_id", "model"):
            value = getattr(self, name)
            if value is not None:
                identifier(value, name)
        nonnegative(self.attempt, "attempt")
        if self.attempt is not None and not 1 <= self.attempt <= 2**63 - 1:
            raise ValueError("attempt must be positive")
        for name in ("start", "end"):
            value = getattr(self, name)
            if value is not None:
                utc(value, name)
        if self.start is not None and self.end is not None and self.start >= self.end:
            raise ValueError("empty or reversed time window")
        if type(self.limit) is not int or not 1 <= self.limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        if type(self.offset) is not int or not 0 <= self.offset <= 1_000_000:
            raise ValueError("offset must be between 0 and 1000000")


@dataclass(frozen=True, kw_only=True)
class QueryResult:
    """Versioned JSON-safe DTO envelope, detached from repository state."""

    data: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        """Return a detached public representation."""
        return deepcopy(self.data)
