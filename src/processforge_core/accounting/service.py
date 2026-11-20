"""Shared scoped query/application seam for future CLI, TUI and plugin clients."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Collection, Iterator, Sequence
from dataclasses import asdict, replace
from datetime import datetime, timezone
from typing import Literal, cast

from processforge_core.accounting.model import (
    METRICS,
    ActivityInterval,
    QueryFilter,
    QueryResult,
    SourceCapability,
    SourceCursor,
    UsageRecord,
    identifier,
    utc,
)
from processforge_core.accounting.rules import clipped, execution_measure, union_seconds
from processforge_core.accounting.storage import (
    Fact,
    Kind,
    SQLiteAccountingRepository,
    timestamp,
)


class AccountingService:
    """Coordinate concrete storage and pure rules without provider or lifecycle code."""

    def __init__(
        self,
        repository: SQLiteAccountingRepository,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Inject durable storage and an optional UTC clock for deterministic snapshots."""
        self.repository = repository
        self.clock = clock if clock is not None else lambda: datetime.now(timezone.utc)

    def ingest(
        self,
        usage: Sequence[UsageRecord] = (),
        activity: Sequence[ActivityInterval] = (),
        *,
        cursor: SourceCursor | None = None,
        capabilities: Sequence[SourceCapability] = (),
    ) -> int:
        """Accept an already normalized batch; return newly stored revision count."""
        return self.repository.ingest(
            usage, activity, cursor=cursor, capabilities=capabilities
        )

    @staticmethod
    def _scope(allowed: Collection[str], filters: QueryFilter) -> list[str]:
        if isinstance(allowed, (str, bytes)):
            raise ValueError("allowed_project_ids must be a collection of ids")
        projects = sorted(set(allowed))
        if len(projects) > 500:
            raise ValueError("allowed project scope exceeds 500")
        for project in projects:
            identifier(project, "allowed project id")
        if filters.project_id is not None:
            if filters.project_id not in projects:
                raise PermissionError("project outside allowed scope")
            return [filters.project_id]
        return projects

    def _as_of(self) -> str:
        now = self.clock()
        utc(now, "clock")
        return timestamp(now)

    def summary(
        self,
        allowed_project_ids: Collection[str],
        filters: QueryFilter | None = None,
    ) -> QueryResult:
        """Aggregate all filtered contributions independently of detail pagination."""
        filters = filters if filters is not None else QueryFilter()
        projects = self._scope(allowed_project_ids, filters)
        with self.repository.snapshot() as connection:
            return QueryResult(
                data=self._summary(connection, projects, filters, self._as_of())
            )

    def details(
        self,
        allowed_project_ids: Collection[str],
        filters: QueryFilter | None = None,
        *,
        kind: Literal["usage", "activity"] = "usage",
    ) -> QueryResult:
        """Return a stable bounded current-fact page with redacted private provenance."""
        if kind not in ("usage", "activity"):
            raise ValueError("invalid detail kind")
        filters = filters if filters is not None else QueryFilter()
        projects = self._scope(allowed_project_ids, filters)
        with self.repository.snapshot() as connection:
            result = self._summary(connection, projects, filters, self._as_of())
            items = [
                self._public(fact)
                for fact in self.repository.facts(
                    connection,
                    projects,
                    filters,
                    kind,
                    page=True,
                )
            ]
            predicate, values = self.repository.where(projects, filters, kind)
            count = connection.execute(
                f"SELECT COUNT(*) FROM current_facts c WHERE {predicate}",
                values,
            ).fetchone()[0]
            result.update(
                {
                    "kind": kind,
                    "items": items,
                    "pagination": self._pagination(filters, count),
                }
            )
            return QueryResult(data=result)

    def projects(
        self,
        allowed_project_ids: Collection[str],
        filters: QueryFilter | None = None,
    ) -> QueryResult:
        """List scoped projects and their summaries using the same pinned snapshot."""
        filters = filters if filters is not None else QueryFilter()
        projects = self._scope(allowed_project_ids, filters)
        with self.repository.snapshot() as connection:
            as_of = self._as_of()
            observed: set[str] = set()
            for kind in ("usage", "activity"):
                predicate, values = self.repository.where(
                    projects, filters, cast(Kind, kind)
                )
                observed.update(
                    row[0]
                    for row in connection.execute(
                        f"SELECT DISTINCT c.project_id FROM current_facts c WHERE {predicate}",
                        values,
                    )
                )
            if not any(
                value is not None
                for value in (
                    filters.assignment_id,
                    filters.run_id,
                    filters.attempt,
                    filters.model,
                )
            ):
                for row in self._capabilities(connection, projects, filters):
                    observed.add(str(row["project_id"]))
            project_ids = sorted(observed)
            page = project_ids[filters.offset : filters.offset + filters.limit]
            result = self._summary(connection, projects, filters, as_of)
            result["items"] = [
                {
                    "project_id": project,
                    "summary": self._summary(
                        connection,
                        [project],
                        replace(filters, project_id=project),
                        as_of,
                    ),
                }
                for project in page
            ]
            result["pagination"] = self._pagination(filters, len(project_ids))
            return QueryResult(data=result)

    @staticmethod
    def _pagination(filters: QueryFilter, count: int) -> dict[str, object]:
        following = filters.offset + filters.limit
        return {
            "limit": filters.limit,
            "offset": filters.offset,
            "total": count,
            "next_offset": following if following < count else None,
        }

    @staticmethod
    def _public(fact: Fact) -> dict[str, object]:
        result: dict[str, object] = {
            "key": asdict(fact.key),
            "revision": fact.revision,
            "attribution": asdict(fact.attribution),
            "quality": fact.quality,
            "adapter_version": fact.provenance.adapter_version,
        }
        if isinstance(fact, UsageRecord):
            result.update(
                {
                    "occurred_at": timestamp(fact.occurred_at),
                    "tokens": {**asdict(fact.tokens), "total": fact.tokens.total},
                }
            )
        else:
            result.update(
                {
                    "start": timestamp(fact.start),
                    "end": timestamp(fact.end) if fact.end is not None else None,
                    "confirmed_end": timestamp(fact.confirmed_end)
                    if fact.confirmed_end is not None
                    else None,
                    "elapsed_seconds": fact.elapsed_seconds,
                    "utc_span_seconds": fact.utc_span_seconds,
                    "clock_discrepancy_seconds": fact.clock_discrepancy_seconds,
                    "clock_quality": fact.clock_quality,
                    "partial": fact.end is None
                    or fact.quality != "measured"
                    or fact.clock_quality != "aligned",
                }
            )
        return result

    @staticmethod
    def _capabilities(
        connection: sqlite3.Connection,
        projects: Sequence[str],
        filters: QueryFilter,
    ) -> Iterator[dict[str, object]]:
        if not projects:
            return
        predicate = f"project_id IN ({','.join('?' for _ in projects)})"
        values: list[object] = list(projects)
        if filters.source_id is not None:
            predicate += " AND source_id=?"
            values.append(filters.source_id)
        # Source inventory is current, not a receipt; calendar/task/model filters
        # do not erase missing source declarations for the selected projects.
        for row in connection.execute(
            f"SELECT payload FROM source_capabilities WHERE {predicate}",
            values,
        ):
            yield cast(dict[str, object], json.loads(row[0]))

    def _summary(
        self,
        connection: sqlite3.Connection,
        projects: Sequence[str],
        filters: QueryFilter,
        as_of: str,
    ) -> dict[str, object]:
        names = (*METRICS, "total")
        totals: dict[str, int | None] = dict.fromkeys(names)
        unknown_metrics = dict.fromkeys(names, 0)
        attribution = {
            "usage_task_bound": 0,
            "usage_project_unassigned": 0,
            "activity_task_bound": 0,
            "activity_project_unassigned": 0,
        }
        usage_count = 0
        partial_usage = 0
        unknown_usage = 0
        for fact in self.repository.facts(connection, projects, filters, "usage"):
            assert isinstance(fact, UsageRecord)
            usage_count += 1
            partial_usage += fact.quality == "partial"
            unknown_usage += fact.quality == "unknown"
            key = (
                "usage_task_bound"
                if fact.attribution.assignment_id
                else "usage_project_unassigned"
            )
            attribution[key] += 1
            for name in names:
                value = getattr(fact.tokens, name)
                if value is None:
                    unknown_metrics[name] += 1
                else:
                    totals[name] = (totals[name] or 0) + value

        activity_count = 0
        partial_activity = 0
        unknown_activity = 0
        unknown_duration = 0
        execution: float | None = None
        execution_partial = False
        clock_quality = dict.fromkeys(
            (
                "aligned",
                "discrepant",
                "reversed",
                "utc_only",
                "monotonic_only",
                "unknown",
            ),
            0,
        )
        current_agent: tuple[str, str] | None = None
        agent_intervals: list[ActivityInterval] = []

        def add_agent() -> None:
            nonlocal execution, execution_partial
            if not agent_intervals:
                return
            seconds, partial = execution_measure(agent_intervals, filters)
            execution_partial = execution_partial or partial
            if seconds is not None:
                execution = (execution or 0.0) + seconds

        for fact in self.repository.facts(
            connection, projects, filters, "activity", order="agent"
        ):
            assert isinstance(fact, ActivityInterval)
            activity_count += 1
            partial_activity += (
                fact.end is None
                or fact.quality == "partial"
                or fact.clock_quality != "aligned"
            )
            unknown_activity += fact.quality == "unknown"
            clock_quality[fact.clock_quality] += 1
            key = (
                "activity_task_bound"
                if fact.attribution.assignment_id
                else "activity_project_unassigned"
            )
            attribution[key] += 1
            agent = (fact.key.origin_id, fact.attribution.agent_instance_id)
            if agent != current_agent:
                add_agent()
                agent_intervals = []
                current_agent = agent
            agent_intervals.append(fact)
            unknown_duration += execution_measure([fact], filters)[0] is None
        add_agent()

        def spans() -> Iterator[tuple[datetime, datetime]]:
            for interval in self.repository.facts(
                connection, projects, filters, "activity", order="time"
            ):
                assert isinstance(interval, ActivityInterval)
                span = clipped(interval, filters)
                if span is not None:
                    yield span

        occupied = union_seconds(spans())
        sources = {"available": 0, "missing": 0, "partial": 0, "unsupported": 0}
        unsupported_metrics = dict.fromkeys((*METRICS, "activity"), 0)
        latest_observation: str | None = None
        for capability in self._capabilities(connection, projects, filters):
            sources[str(capability["status"])] += 1
            supported = cast(list[str], capability["supported_metrics"])
            for metric in unsupported_metrics:
                unsupported_metrics[metric] += metric not in supported
            observed_at = str(capability["observed_at"])
            latest_observation = (
                max(latest_observation, observed_at)
                if latest_observation
                else observed_at
            )
        observed_source_count = 0
        for kind in ("usage", "activity"):
            # Count by project and origin, not just display source name.
            predicate, values = self.repository.where(
                projects, filters, cast(Kind, kind)
            )
            if kind == "usage":
                usage_predicate, usage_values = predicate, values
            else:
                observed_source_count = connection.execute(
                    "SELECT COUNT(*) FROM (SELECT c.project_id,c.origin_id,c.source_id "
                    f"FROM current_facts c WHERE {usage_predicate} UNION "
                    "SELECT c.project_id,c.origin_id,c.source_id "
                    f"FROM current_facts c WHERE {predicate})",
                    [*usage_values, *values],
                ).fetchone()[0]
        filter_dto: dict[str, object] = asdict(filters)
        filter_dto["start"] = timestamp(filters.start) if filters.start else None
        filter_dto["end"] = timestamp(filters.end) if filters.end else None
        return {
            "schema_version": 1,
            "as_of": as_of,
            "filters": filter_dto,
            "totals": totals,
            "execution_seconds": execution,
            "execution_quality": "unknown"
            if execution is None
            else "lower_bound"
            if execution_partial
            else "measured",
            "occupied_seconds": occupied,
            "occupied_quality": "unknown"
            if occupied is None
            else "partial"
            if partial_activity or unknown_activity
            else "measured",
            "attribution": attribution,
            "coverage": {
                "basis": "observed_facts_and_declared_sources",
                "complete": False,
                "usage_records": usage_count,
                "activity_intervals": activity_count,
                "partial_usage": partial_usage,
                "unknown_usage": unknown_usage,
                "partial_activity": partial_activity,
                "unknown_activity": unknown_activity,
                "unknown_duration": unknown_duration,
                "clock_quality": clock_quality,
                "unknown_metrics": unknown_metrics,
                "declared_sources": sources,
                "observed_sources": observed_source_count,
                "unsupported_metrics": unsupported_metrics,
                "latest_source_observation": latest_observation,
                "inventory_known": sum(sources.values()) > 0,
                "quarantine_excluded": True,
                "open_tail_policy": "confirmed_lower_bound_only",
            },
        }
