"""Read-only canonical queries over an explicitly supplied existing snapshot.

The trusted binder MUST authorize the project, verify physical store identity,
Work generation, canonical completeness and readiness before passing a
SqlSession from Database.read or an authorized Database.transaction. The
constructor conveys no authority and does no I/O. Database/driver own the
snapshot, store identity, operation/thread lifetime and cleanup; read() opens
SQLite mode=ro. A transaction session permits repository writes, but this
reader issues only SELECT. SqlSession exposes no transaction/mode introspection:
the trusted binder must supply a live session from that owning operation.
Each call checks the registered descriptor and project coverage/revision,
and never begins/ends a transaction.
These checks are not a substitute for the binder's host authorization.

Only bounded summary columns are read. Active queries explicitly drive outer
partial Run indexes then per-Run edge seeks. Complete legacy output can be
large: cost follows A+P or C, not a constant. Objective history visits the
matching local/fallback streams (including excluded bootstrap matches), not
unrelated history. No YAML, body discovery, backfill or mutation is available.
"""

from __future__ import annotations

from typing import Any, Literal

from ..database.contracts import SqlSession, SqlStatement
from ..database.errors import DatabaseError
from .selection_contract import (
    CandidateSet,
    SelectionCandidate,
    SelectionError,
    SelectionRowKey,
    _selector,
    _text,
    normalize_objective,
)
from .selection_schema import selection_schema

__all__ = ("CanonicalSelectionQueries",)

_ACTIVE = frozenset(("open", "in_progress", "review", "blocked"))
_CAT_RUN = _ACTIVE | {"draft"}
_HISTORICAL = frozenset(("done", "completed", "cancelled", "failed"))
_BOOTSTRAP_PREFIX = "verify processforge project onboarding"
_BOOL_RUN = ("cat_run", "cur_run", "run_bootstrap")
_COUNTERS = (
    "cat_local_n",
    "cur_n",
    "cur_local_n",
    "cat_objective_fallback_n",
    "current_objective_fallback_n",
    "cur_fixed_n",
    "cur_run_bootstrap_n",
    "cur_fixed_local_n",
    "cur_run_bootstrap_local_n",
)
_BOOL_EDGE = (
    "cat_valid",
    "cat_local",
    "cur_visible",
    "cur_local",
    "bootstrap",
    "objective_fallback",
    "current_objective_fallback",
    "created_fallback",
    "updated_fallback",
    "process_fallback",
    "status_fallback",
)
_RUN_TEXT = (
    "p",
    "r",
    "source_order",
    "objective_raw",
    "objective_norm",
    "created_lex",
    "updated_lex",
    "process_raw",
    "status_raw",
)
_EDGE_TEXT = (
    "p",
    "r",
    "a",
    "objective_raw",
    "objective_norm",
    "session_id",
    "updated_lex",
    "created_lex",
    "current_objective_raw",
    "current_objective_norm",
    "bootstrap_mode",
    "current_status_raw",
    "current_assignment_id",
)


class CanonicalSelectionQueries:
    """Session-bound reader; the binder owns snapshot and host authority."""

    def __init__(self, session: SqlSession, *, project_uuid: str) -> None:
        if not callable(getattr(session, "stream", None)):
            raise SelectionError("selection_input_invalid")
        self._project = _text(project_uuid, nonempty=True)
        self._session = session

    def _fetch(
        self, sql: str, params: tuple[str | int, ...] = ()
    ) -> list[dict[str, Any]]:
        try:
            with self._session.stream(SqlStatement(sql, params)) as rows:
                return [dict(zip(row.columns, row.values, strict=True)) for row in rows]
        except DatabaseError:
            raise SelectionError("selection_store_unavailable") from None

    def _snapshot(self) -> int:
        schema = selection_schema()
        if self._fetch(
            "SELECT version,checksum FROM pf_schema_versions WHERE namespace=?",
            (schema.namespace,),
        ) != [{"version": schema.version, "checksum": schema.checksum}]:
            raise SelectionError("selection_schema_unsupported")
        rows = self._fetch(
            "SELECT catalog_revision,coverage_complete "
            "FROM work_selection_state WHERE p=?",
            (self._project,),
        )
        if (
            len(rows) != 1
            or type(rows[0]["coverage_complete"]) is not int
            or rows[0]["coverage_complete"] != 1
            or type(rows[0]["catalog_revision"]) is not int
            or rows[0]["catalog_revision"] < 1
        ):
            raise SelectionError("selection_coverage_incomplete")
        return rows[0]["catalog_revision"]

    @staticmethod
    def _facts(
        row: dict[str, Any],
        texts: tuple[str, ...],
        booleans: tuple[str, ...],
    ) -> None:
        try:
            for name in texts:
                _text(row[name])
            if any(
                type(row[name]) is not int or row[name] not in (0, 1)
                for name in booleans
            ):
                raise SelectionError("selection_invariant_failed")
            if type(row["revision"]) is not int or row["revision"] < 1:
                raise SelectionError("selection_invariant_failed")
        except (KeyError, SelectionError):
            raise SelectionError("selection_invariant_failed") from None

    def _run(self, row: dict[str, Any]) -> dict[str, Any]:
        self._facts(row, _RUN_TEXT, _BOOL_RUN)
        if (
            row["p"] != self._project
            or not row["r"]
            or any(name not in row for name in _COUNTERS)
            or any(type(row[name]) is not int or row[name] < 0 for name in _COUNTERS)
            or row["cur_n"]
            != row["cur_fixed_n"]
            + (1 - row["run_bootstrap"]) * row["cur_run_bootstrap_n"]
            or row["cur_local_n"]
            != row["cur_fixed_local_n"]
            + (1 - row["run_bootstrap"]) * row["cur_run_bootstrap_local_n"]
            or row["cat_run"] != int(row["status_raw"] in _CAT_RUN)
            or row["cur_run"] != int(row["status_raw"] in _ACTIVE)
            or row["objective_norm"] != normalize_objective(row["objective_raw"])
            or row["run_bootstrap"]
            != int(row["objective_raw"].lower().startswith(_BOOTSTRAP_PREFIX))
        ):
            raise SelectionError("selection_invariant_failed")
        return row

    def _edge(self, row: dict[str, Any]) -> dict[str, Any]:
        self._facts(row, _EDGE_TEXT, _BOOL_EDGE)
        if (
            row["p"] != self._project
            or not row["r"]
            or "ordinal" not in row
            or type(row["ordinal"]) is not int
            or row["ordinal"] < -1
            or row["bootstrap_mode"] not in ("never", "always", "run")
            or row["bootstrap"] != int(row["bootstrap_mode"] == "always")
            or row["objective_norm"] != normalize_objective(row["objective_raw"])
            or row["current_objective_norm"]
            != normalize_objective(row["current_objective_raw"])
            or row["cur_local"]
            != int(not row["status_fallback"] and row["current_status_raw"] in _ACTIVE)
            or (
                row["ordinal"] == -1
                and (row["cat_valid"] or row["a"] or row["bootstrap_mode"] != "never")
            )
        ):
            raise SelectionError("selection_invariant_failed")
        return row

    def _run_at(self, run_id: str, cache: dict[str, dict[str, Any]]) -> dict[str, Any]:
        if run_id not in cache:
            rows = self._fetch(
                "SELECT * FROM work_run_selection WHERE p=? AND r=?",
                (self._project, run_id),
            )
            if len(rows) != 1:
                raise SelectionError("selection_invariant_failed")
            cache[run_id] = self._run(rows[0])
        return cache[run_id]

    def _key(self, edge: dict[str, Any]) -> SelectionRowKey:
        return SelectionRowKey(self._project, edge["r"], edge["ordinal"])

    def _pending(self, edge: dict[str, Any]) -> bool:
        rows = self._fetch(
            "SELECT operation_id FROM work_valid_pending_edges "
            "WHERE p=? AND r=? AND ordinal=?",
            (self._project, edge["r"], edge["ordinal"]),
        )
        if rows:
            if not edge["cat_valid"]:
                raise SelectionError("selection_invariant_failed")
            try:
                _text(rows[0]["operation_id"], nonempty=True)
            except SelectionError:
                raise SelectionError("selection_invariant_failed") from None
        return bool(rows)

    def _candidate(
        self,
        edge: dict[str, Any],
        run: dict[str, Any],
        *,
        model: Literal["catalog", "current"],
    ) -> SelectionCandidate:
        current = model == "current"
        raw = "current_objective_raw" if current else "objective_raw"
        fallback = "current_objective_fallback" if current else "objective_fallback"
        return SelectionCandidate(
            key=self._key(edge),
            assignment_id=edge["current_assignment_id"] if current else edge["a"],
            source_order=run["source_order"],
            objective=run["objective_raw"] if edge[fallback] else edge[raw],
            session_id=edge["session_id"],
            updated_lex=(
                run["updated_lex"] if edge["updated_fallback"] else edge["updated_lex"]
            ),
            created_lex=(
                run["created_lex"] if edge["created_fallback"] else edge["created_lex"]
            ),
            pending_completion=self._pending(edge),
        )

    @staticmethod
    def _ordered(revision: int, rows: list[SelectionCandidate]) -> CandidateSet:
        rows.sort(key=lambda row: (row.source_order, row.key.run_id, row.key.ordinal))
        return CandidateSet(revision, tuple(rows))

    @staticmethod
    def _bootstrap(edge: dict[str, Any], run: dict[str, Any]) -> bool:
        return edge["bootstrap_mode"] == "always" or (
            edge["bootstrap_mode"] == "run" and bool(run["run_bootstrap"])
        )

    def catalog_active(self) -> CandidateSet:
        """Catalog AND predicate union terminal pending, dedup by occurrence."""
        revision = self._snapshot()
        selected: dict[SelectionRowKey, SelectionCandidate] = {}
        runs: dict[str, dict[str, Any]] = {}
        outer = self._fetch(
            "SELECT * FROM work_run_selection INDEXED BY wr_cat "
            "WHERE p=? AND cat_run=1 AND cat_local_n>0 "
            "ORDER BY source_order,r",
            (self._project,),
        )
        for row in outer:
            run = self._run(row)
            runs[run["r"]] = run
            for raw in self._fetch(
                "SELECT * FROM work_selection_edges INDEXED BY we_cat "
                "WHERE p=? AND r=? AND cat_valid=1 AND cat_local=1 "
                "ORDER BY ordinal",
                (self._project, run["r"]),
            ):
                edge = self._edge(raw)
                candidate = self._candidate(edge, run, model="catalog")
                selected[candidate.key] = candidate
        for pending in self._fetch(
            "SELECT r,ordinal,operation_id FROM work_valid_pending_edges "
            "WHERE p=? ORDER BY r,ordinal",
            (self._project,),
        ):
            key = SelectionRowKey(self._project, pending["r"], pending["ordinal"])
            if key in selected:
                continue
            rows = self._fetch(
                "SELECT * FROM work_selection_edges WHERE p=? AND r=? AND ordinal=?",
                (self._project, key.run_id, key.ordinal),
            )
            if len(rows) != 1:
                raise SelectionError("selection_invariant_failed")
            edge = self._edge(rows[0])
            if not edge["cat_valid"]:
                raise SelectionError("selection_invariant_failed")
            run = self._run_at(edge["r"], runs)
            selected[key] = self._candidate(edge, run, model="catalog")
        return self._ordered(revision, list(selected.values()))

    def current_active(self) -> CandidateSet:
        """Current OR predicate, with separate indexed non-bootstrap modes."""
        revision = self._snapshot()
        candidates: list[SelectionCandidate] = []
        for active in (True, False):
            outer_index = "wr_cur_all" if active else "wr_cur_local"
            counter = "cur_n" if active else "cur_local_n"
            edge_index = "we_cur_mode" if active else "we_cur_local_mode"
            local = "" if active else " AND cur_local=1"
            for row in self._fetch(
                f"SELECT * FROM work_run_selection INDEXED BY {outer_index} "
                f"WHERE p=? AND cur_run=? AND {counter}>0 "
                "ORDER BY source_order,r",
                (self._project, int(active)),
            ):
                run = self._run(row)
                modes = ("never",) if run["run_bootstrap"] else ("never", "run")
                for mode in modes:
                    for raw in self._fetch(
                        "SELECT * FROM work_selection_edges "
                        f"INDEXED BY {edge_index} WHERE p=? AND r=? "
                        f"AND cur_visible=1{local} AND bootstrap_mode=? "
                        "ORDER BY ordinal",
                        (self._project, run["r"], mode),
                    ):
                        candidates.append(
                            self._candidate(self._edge(raw), run, model="current")
                        )
        return self._ordered(revision, candidates)

    def exact_members(
        self, *, run_id: str, assignment_id: str
    ) -> tuple[SelectionRowKey, ...]:
        """Return catalog-valid occurrence keys, never a semantic pair proof."""
        _selector(run_id)
        _selector(assignment_id)
        self._snapshot()
        return tuple(
            self._key(self._edge(row))
            for row in self._fetch(
                "SELECT * FROM work_selection_edges INDEXED BY we_assignment "
                "WHERE p=? AND a=? AND r=? AND cat_valid=1 ORDER BY ordinal",
                (self._project, assignment_id, run_id),
            )
        )

    def run_choice(self, *, run_id: str) -> tuple[SelectionRowKey, ...]:
        """At most two memberships; duplicates still require a choice."""
        _selector(run_id)
        self._snapshot()
        return tuple(
            self._key(self._edge(row))
            for row in self._fetch(
                "SELECT * FROM work_selection_edges INDEXED BY we_valid "
                "WHERE p=? AND r=? AND cat_valid=1 ORDER BY ordinal LIMIT 2",
                (self._project, run_id),
            )
        )

    def assignment_members(self, *, assignment_id: str) -> tuple[SelectionRowKey, ...]:
        """All D memberships sorted by legacy Run traversal then ordinal."""
        _selector(assignment_id)
        self._snapshot()
        cache: dict[str, dict[str, Any]] = {}
        rows = [
            self._edge(row)
            for row in self._fetch(
                "SELECT * FROM work_selection_edges INDEXED BY we_assignment "
                "WHERE p=? AND a=? AND cat_valid=1",
                (self._project, assignment_id),
            )
        ]
        rows.sort(
            key=lambda edge: (
                self._run_at(edge["r"], cache)["source_order"],
                edge["r"],
                edge["ordinal"],
            )
        )
        return tuple(self._key(edge) for edge in rows)

    def objective_history(
        self, *, objective: str, model: Literal["catalog", "current"]
    ) -> CandidateSet:
        """Return only historical matches; current 'other' is not history."""
        normalized = normalize_objective(objective)
        if type(model) is not str or model not in ("catalog", "current"):
            raise SelectionError("selection_input_invalid")
        revision = self._snapshot()
        catalog = model == "catalog"
        prefix = "cat" if catalog else "current"
        visible = "cat_valid" if catalog else "cur_visible"
        objective_column = "objective_norm" if catalog else "current_objective_norm"
        fallback = "objective_fallback" if catalog else "current_objective_fallback"
        cache: dict[str, dict[str, Any]] = {}
        candidates: list[SelectionCandidate] = []

        def collect(raw: dict[str, Any], run: dict[str, Any]) -> None:
            edge = self._edge(raw)
            if catalog:
                active = bool(run["cat_run"] and edge["cat_local"])
                if active or self._pending(edge):
                    return
            else:
                if self._bootstrap(edge, run):
                    return
                status = (
                    run["status_raw"]
                    if edge["status_fallback"]
                    else edge["current_status_raw"]
                )
                if status in _ACTIVE or run["cur_run"]:
                    return
                if status not in _HISTORICAL and run["status_raw"] not in _HISTORICAL:
                    return
            candidates.append(self._candidate(edge, run, model=model))

        for raw in self._fetch(
            "SELECT * FROM work_selection_edges "
            f"INDEXED BY we_{prefix}_objective_local "
            f"WHERE p=? AND {objective_column}=? AND {visible}=1 "
            f"AND {fallback}=0",
            (self._project, normalized),
        ):
            collect(raw, self._run_at(raw["r"], cache))
        for raw_run in self._fetch(
            "SELECT * FROM work_run_selection "
            f"INDEXED BY wr_{prefix}_objective_fallback "
            "WHERE p=? AND objective_norm=? "
            f"AND {prefix}_objective_fallback_n>0 "
            "ORDER BY source_order,r",
            (self._project, normalized),
        ):
            run = self._run(raw_run)
            cache[run["r"]] = run
            for raw in self._fetch(
                "SELECT * FROM work_selection_edges "
                f"INDEXED BY we_{prefix}_objective_fallback "
                f"WHERE p=? AND r=? AND {visible}=1 AND {fallback}=1 "
                "ORDER BY ordinal",
                (self._project, run["r"]),
            ):
                collect(raw, run)
        return self._ordered(revision, candidates)
