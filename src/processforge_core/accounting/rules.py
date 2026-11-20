"""Pure counter and interval rules independent of adapters and persistence."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime

from processforge_core.accounting.model import ActivityInterval, QueryFilter


def clipped(
    interval: ActivityInterval, filters: QueryFilter
) -> tuple[datetime, datetime] | None:
    """Intersect confirmed activity with a query window without inventing a tail."""
    end = interval.confirmed_end
    if end is None:
        return None
    start = max(interval.start, filters.start) if filters.start else interval.start
    end = min(end, filters.end) if filters.end else end
    return (start, end) if start <= end else None


def union_seconds(spans: Iterable[tuple[datetime, datetime]]) -> float | None:
    """Union spans ordered by start using constant memory; no observations is unknown."""
    current_end: datetime | None = None
    seconds = 0.0
    seen = False
    for start, end in spans:
        seen = True
        if current_end is None or start > current_end:
            seconds += (end - start).total_seconds()
        elif end > current_end:
            seconds += (end - current_end).total_seconds()
        current_end = max(current_end, end) if current_end is not None else end
    return seconds if seen else None


def execution_measure(
    intervals: Sequence[ActivityInterval], filters: QueryFilter
) -> tuple[float | None, bool]:
    """Return one agent's confirmed seconds and whether they are a lower bound.

    UTC-aligned measurements permit calendar clipping and union. Independent
    clocks only justify an elapsed total for a fully included interval. Without
    monotonic endpoints, overlapping independent measurements cannot be unioned:
    use the largest confirmed duration (or aligned union) as a lower bound.
    Open measurements have no calendar placement beyond their observed start.
    """
    values: list[float] = []
    aligned_spans: list[tuple[datetime, datetime]] = []
    partial = False
    all_aligned = True
    for interval in intervals:
        aligned = interval.clock_quality == "aligned" and interval.quality != "unknown"
        all_aligned = all_aligned and aligned
        partial = partial or interval.end is None or interval.quality != "measured"
        if interval.elapsed_seconds is None or interval.quality == "unknown":
            partial = True
            continue
        if aligned:
            span = clipped(interval, filters)
            if span is not None:
                aligned_spans.append(span)
                # Preserve the observed monotonic value when no clipping is needed.
                values.append(
                    interval.elapsed_seconds
                    if span == (interval.start, interval.end)
                    else (span[1] - span[0]).total_seconds()
                )
                continue
        elif interval.end is not None:
            first, last = sorted((interval.start, interval.end))
            if (filters.start is None or filters.start <= first) and (
                filters.end is None or filters.end >= last
            ):
                values.append(interval.elapsed_seconds)
                continue
        elif filters.start is None and filters.end is None:
            values.append(interval.elapsed_seconds)
            continue
        partial = True

    if not values:
        return None, True
    if len(intervals) == 1:
        return values[0], partial
    aligned_seconds = union_seconds(sorted(aligned_spans))
    if all_aligned:
        return aligned_seconds, partial
    # Never sum possibly overlapping measurements of the same agent, including
    # nested, open or backwards-clock observations from different sources.
    return max(max(values), aligned_seconds or 0.0), True
