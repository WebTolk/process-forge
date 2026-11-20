"""Transaction-local before/after arithmetic over indexed membership facts.

Run edits update one summary row. Assignment edits have honest indexed O(D)
fanout. No ordinary operation recounts edges or traverses historic records.
Initial coverage is an importer/writer-fence obligation, not inferred here.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import cast

from ..database import SqlSession, SqlStatement, SqlValue
from .compact_codec import decode_canonical
from .compact_model import JsonValue
from .mutation_codec import document, raw_text
from .mutation_model import Encoded, EntityKey, MutationError, MutationPlan, integer
from .selection_contract import normalize_objective

Row = dict[str, SqlValue]
_ACTIVE = frozenset(("open", "in_progress", "review", "blocked"))
_CAT_RUN = _ACTIVE | {"draft"}
_CAT_TASK = _ACTIVE | {"draft", "ready", "pending", "debugging", "ready_for_review"}
_PREFIX = "verify processforge project onboarding"
_ID = re.compile(r"(?:[a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])")
_COUNTERS = (
    "cat_local_n",
    "cur_fixed_n",
    "cur_run_bootstrap_n",
    "cur_fixed_local_n",
    "cur_run_bootstrap_local_n",
    "cat_objective_fallback_n",
    "current_objective_fallback_n",
)


def one(sql: SqlSession, query: str, args: tuple[SqlValue, ...]) -> Row | None:
    """Detach one fixed-query row without leaking SQL sessions to the caller."""
    result = sql.fetch_one(SqlStatement(query, args))
    return None if result is None else dict(zip(result.columns, result.values))


def rows(sql: SqlSession, query: str, args: tuple[SqlValue, ...]) -> tuple[Row, ...]:
    """Consume only explicitly indexed current fanout, never history for mutation."""
    with sql.stream(SqlStatement(query, args)) as stream:
        return tuple(dict(zip(row.columns, row.values)) for row in stream)


def write(sql: SqlSession, query: str, args: tuple[SqlValue, ...]) -> None:
    """Every single-row insert/update/delete must affect exactly one row."""
    if sql.execute(SqlStatement(query, args)).affected_rows != 1:
        raise MutationError("mutation_cas_conflict")


def insert(sql: SqlSession, table: str, row: Row) -> None:
    """Internal helper; table/column identifiers come exclusively from code."""
    write(
        sql,
        f"INSERT INTO {table}({','.join(row)}) VALUES({','.join('?' for _ in row)})",
        tuple(row.values()),
    )


def string(row: Row, key: str) -> str:
    """Fail closed on stored type corruption instead of SQL coercion."""
    value = row[key]
    if type(value) is not str:
        raise MutationError("selection_invariant_failed")
    return value


def number(row: Row, key: str, minimum: int = 0) -> int:
    """Require an actual int64 in a stored counter or revision."""
    try:
        return integer(row[key], minimum)
    except MutationError:
        raise MutationError("selection_invariant_failed") from None


def entity(sql: SqlSession, p: str, key: EntityKey) -> Row | None:
    """Address one current entity by primary key."""
    return one(
        sql,
        "SELECT * FROM work_entities WHERE project_id=? AND kind=? AND entity_id=?",
        (p, key.kind, key.entity_id),
    )


def body(row: Row | None) -> Mapping[str, JsonValue] | None:
    """Missing and present-empty bodies are different facts."""
    if row is None:
        return None
    from .mutation_codec import digest

    encoded = Encoded(
        string(row, "payload").encode("utf-8"), number(row, "payload_version", 1)
    )
    if (
        digest(encoded) != row["payload_hash"]
        or row["deleted"] != 0
        or row["source_ref"] is not None
    ):
        raise MutationError("mutation_current_state_unsupported")
    data = document(encoded)
    session = data.get("session")
    objective = raw_text(data.get("objective"))
    summaries = dict(
        status_raw=raw_text(data.get("status")),
        objective_raw=objective,
        objective_normalized=normalize_objective(objective),
        created_lex=raw_text(data.get("created_at")),
        updated_lex=raw_text(data.get("updated_at")),
        process_ref=raw_text(data.get("process")),
        context_ref=raw_text(data.get("context_id")),
        session_id=raw_text(session.get("id")) if isinstance(session, Mapping) else "",
    )
    if any(row[k] != v for k, v in summaries.items()):
        raise MutationError("selection_invariant_failed")
    return data


def _get(data: Mapping[str, JsonValue], key: str) -> str:
    return raw_text(data.get(key))


def run_facts(data: Mapping[str, JsonValue], order: str) -> Row:
    """Metadata-only facts; fallback edge values are resolved on reads."""
    status, objective = _get(data, "status"), _get(data, "objective")
    return dict(
        source_order=order,
        cat_run=int(status in _CAT_RUN),
        cur_run=int(status in _ACTIVE),
        objective_raw=objective,
        objective_norm=normalize_objective(objective),
        created_lex=_get(data, "created_at"),
        updated_lex=_get(data, "updated_at"),
        process_raw=_get(data, "process"),
        status_raw=status,
        run_bootstrap=int(objective.lower().startswith(_PREFIX)),
    )


def edge_facts(
    p: str,
    r: str,
    ordinal: int,
    member: JsonValue,
    task: Mapping[str, JsonValue] | None,
) -> Row:
    """Reduce legacy catalog/current local facts, preserving raw occurrences."""
    synthetic = ordinal == -1
    visible = synthetic or isinstance(member, Mapping)
    entry = member if isinstance(member, Mapping) else {}
    entry_id = _get(entry, "id")
    missing = task is None and not synthetic
    current = (
        {"id": entry.get("id"), "status": entry.get("status")}
        if missing
        else task or {}
    )
    current_id = _get(current, "id")
    objective = _get(task or {}, "objective")
    cur_objective = _get(current, "objective")
    own_status = _get(current, "status")
    resolved = _get(task or {}, "id") or entry_id
    valid = bool(
        visible
        and not synthetic
        and _ID.fullmatch(r)
        and entry_id
        and _ID.fullmatch(entry_id)
        and task
        and _ID.fullmatch(resolved)
        and (_get(task, "run_id") or r) == r
    )
    cat_status = _get(task or {}, "status") or _get(entry, "status")
    mode = (
        "always"
        if current_id == "first-assignment" or cur_objective.lower().startswith(_PREFIX)
        else "run"
        if missing
        else "never"
    )
    if not visible:
        mode = "never"
    session = (task or {}).get("session")
    return dict(
        p=p,
        r=r,
        ordinal=ordinal,
        a=resolved if valid else "",
        cat_valid=int(valid),
        cat_local=int(valid and cat_status in _CAT_TASK),
        cur_visible=int(visible),
        cur_local=int(visible and own_status in _ACTIVE),
        bootstrap=int(mode == "always"),
        objective_raw=objective,
        objective_norm=normalize_objective(objective),
        session_id=_get(session, "id") if isinstance(session, Mapping) else "",
        updated_lex=_get(task or {}, "updated_at"),
        created_lex=_get(task or {}, "created_at"),
        objective_fallback=int(not objective),
        current_objective_raw=cur_objective,
        current_objective_norm=normalize_objective(cur_objective),
        current_objective_fallback=int(not cur_objective),
        created_fallback=int(not _get(task or {}, "created_at")),
        updated_fallback=int(not _get(task or {}, "updated_at")),
        process_fallback=int(not _get(task or {}, "process")),
        bootstrap_mode=mode,
        status_fallback=int(not own_status),
        current_status_raw=own_status,
        current_assignment_id=current_id,
    )


def contribution(edge: Row | None) -> tuple[int, ...]:
    """Seven independent counts; derived current totals depend on Run only."""
    if edge is None:
        return (0,) * 7
    for key in (
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
    ):
        if number(edge, key) not in (0, 1):
            raise MutationError("selection_invariant_failed")
    mode = string(edge, "bootstrap_mode")
    if mode not in ("never", "always", "run") or edge["bootstrap"] != int(
        mode == "always"
    ):
        raise MutationError("selection_invariant_failed")
    v, c, u = (
        number(edge, "cat_valid"),
        number(edge, "cur_visible"),
        number(edge, "cur_local"),
    )
    return (
        v * number(edge, "cat_local"),
        c * int(mode == "never"),
        c * int(mode == "run"),
        c * u * int(mode == "never"),
        c * u * int(mode == "run"),
        v * number(edge, "objective_fallback"),
        c * number(edge, "current_objective_fallback"),
    )


def _counts(row: Row) -> tuple[int, ...]:
    values = tuple(number(row, key) for key in _COUNTERS)
    boot = number(row, "run_bootstrap")
    if (
        boot not in (0, 1)
        or number(row, "cur_n") != values[1] + (1 - boot) * values[2]
        or number(row, "cur_local_n") != values[3] + (1 - boot) * values[4]
        or values[3] > values[1]
        or values[4] > values[2]
    ):
        raise MutationError("selection_invariant_failed")
    return values


class SelectionUpdater:
    """Private fixed algorithm owned by one repository transaction."""

    def __init__(self, sql: SqlSession, p: str, plan: MutationPlan) -> None:
        self.sql, self.p = sql, p
        self.run_ids = {
            e.after.key.entity_id for e in plan.entities if e.after.key.kind == "run"
        }
        self.occurrences = {(m.run_id, m.ordinal) for m in plan.members}
        for edit in plan.entities:
            if edit.after.key.kind != "assignment":
                continue
            a = edit.after.key.entity_id
            for row in rows(
                sql,
                "SELECT run_id,ordinal FROM work_members INDEXED BY work_member_lookup WHERE project_id=? AND assignment_ref=?",
                (p, a),
            ):
                self.occurrences.add((string(row, "run_id"), number(row, "ordinal")))
            for row in rows(
                sql,
                "SELECT r,ordinal FROM work_selection_edges INDEXED BY we_assignment WHERE p=? AND a=?",
                (p, a),
            ):
                self.occurrences.add((string(row, "r"), number(row, "ordinal", -1)))
        self.run_ids.update(r for r, _ in self.occurrences)
        self.read_set = {e.key for e in plan.proof.entities}
        if any(EntityKey("run", r) not in self.read_set for r in self.run_ids):
            raise MutationError("mutation_read_set_incomplete")
        for change in plan.members:
            self.occurrences.add((change.run_id, -1))
        self.before_runs: dict[str, Row | None] = {}
        for r in sorted(self.run_ids):
            before = one(
                sql, "SELECT * FROM work_run_selection WHERE p=? AND r=?", (p, r)
            )
            run = entity(sql, p, EntityKey("run", r))
            if (before is None) != (run is None):
                raise MutationError("selection_invariant_failed")
            if before is not None and run is not None:
                _counts(before)
                if any(
                    before[k] != v
                    for k, v in run_facts(
                        cast(Mapping[str, JsonValue], body(run)),
                        string(run, "source_order"),
                    ).items()
                ):
                    raise MutationError("selection_invariant_failed")
            else:
                self.occurrences.add((r, -1))
            self.before_runs[r] = before
        self.before_edges: dict[tuple[str, int], Row | None] = {}
        for r, ordinal in sorted(self.occurrences):
            edge = one(
                sql,
                "SELECT * FROM work_selection_edges WHERE p=? AND r=? AND ordinal=?",
                (p, r, ordinal),
            )
            expected = self._edge(r, ordinal)
            if (edge is None) != (expected is None) or (
                edge is not None
                and expected is not None
                and any(edge[k] != v for k, v in expected.items())
            ):
                raise MutationError("selection_invariant_failed")
            if edge is not None:
                contribution(edge)
                number(edge, "revision", 1)
            self.before_edges[r, ordinal] = edge

    def _edge(self, r: str, ordinal: int) -> Row | None:
        if entity(self.sql, self.p, EntityKey("run", r)) is None:
            return None
        if ordinal == -1:
            if (
                one(
                    self.sql,
                    "SELECT ordinal FROM work_members WHERE project_id=? AND run_id=? LIMIT 1",
                    (self.p, r),
                )
                is not None
            ):
                return None
            return edge_facts(self.p, r, ordinal, None, {})
        member = one(
            self.sql,
            "SELECT * FROM work_members WHERE project_id=? AND run_id=? AND ordinal=?",
            (self.p, r, ordinal),
        )
        if member is None:
            return None
        raw = decode_canonical(string(member, "member_payload").encode("utf-8"))
        ref = _get(raw, "id") if isinstance(raw, Mapping) else ""
        status = _get(raw, "status") if isinstance(raw, Mapping) else ""
        if member["assignment_ref"] != ref or member["member_status"] != status:
            raise MutationError("selection_invariant_failed")
        if ref and EntityKey("assignment", ref) not in self.read_set:
            raise MutationError("mutation_read_set_incomplete")
        task = entity(self.sql, self.p, EntityKey("assignment", ref)) if ref else None
        return edge_facts(self.p, r, ordinal, raw, body(task))

    def apply(self) -> None:
        """Apply edge differences and one counter statement per affected Run."""
        deltas = {r: [0] * 7 for r in self.run_ids}
        after_edges = {key: self._edge(*key) for key in sorted(self.occurrences)}
        for key, after in after_edges.items():
            before = self.before_edges[key]
            left, right = contribution(before), contribution(after)
            for i in range(7):
                deltas[key[0]][i] += right[i] - left[i]
        # Insert parents before edges; existing rows use one combined counter CAS.
        for r in sorted(self.run_ids):
            before = self.before_runs[r]
            current = entity(self.sql, self.p, EntityKey("run", r))
            if current is None:
                raise MutationError("selection_invariant_failed")
            data = body(current)
            assert data is not None
            facts = run_facts(data, string(current, "source_order"))
            old = _counts(before) if before is not None else (0,) * 7
            counts = tuple(integer(old[i] + deltas[r][i]) for i in range(7))
            facts.update(dict(zip(_COUNTERS, counts)))
            boot = cast(int, facts["run_bootstrap"])
            facts.update(
                cur_n=integer(counts[1] + (1 - boot) * counts[2]),
                cur_local_n=integer(counts[3] + (1 - boot) * counts[4]),
            )
            _counts(facts)
            facts["revision"] = (
                integer(number(before, "revision", 1) + 1, 1)
                if before is not None
                else 1
            )
            if before is None:
                insert(self.sql, "work_run_selection", dict(p=self.p, r=r, **facts))
            else:
                write(
                    self.sql,
                    "UPDATE work_run_selection SET "
                    + ",".join(k + "=?" for k in facts)
                    + " WHERE p=? AND r=? AND revision=?",
                    (*facts.values(), self.p, r, before["revision"]),
                )
        for (r, ordinal), after in after_edges.items():
            before = self.before_edges[r, ordinal]
            if after is None:
                if before is not None:
                    write(
                        self.sql,
                        "DELETE FROM work_selection_edges WHERE p=? AND r=? AND ordinal=? AND revision=?",
                        (self.p, r, ordinal, before["revision"]),
                    )
            elif before is None:
                insert(self.sql, "work_selection_edges", dict(after, revision=1))
            else:
                after["revision"] = integer(number(before, "revision", 1) + 1, 1)
                fields = {
                    k: v for k, v in after.items() if k not in ("p", "r", "ordinal")
                }
                write(
                    self.sql,
                    "UPDATE work_selection_edges SET "
                    + ",".join(k + "=?" for k in fields)
                    + " WHERE p=? AND r=? AND ordinal=? AND revision=?",
                    (*fields.values(), self.p, r, ordinal, before["revision"]),
                )
