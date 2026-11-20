"""Authored regression specifications; execute only under registered QA.

The oracle calls the actual legacy catalog/current services, not a second
implementation of their selectors. The fixture encoder is deliberately
test-only: it is not a migration tool or an additional canonical writer.
"""

from __future__ import annotations

import copy
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import TypedDict, cast
from uuid import uuid4

import pytest

from processforge_core.database import (
    Database,
    DatabaseIdentity,
    DatabaseTarget,
    SchemaManager,
    SqlStatement,
)
from processforge_core.database.sqlite import SQLiteDriver
from processforge_core.process_execution import (
    ACTIVE_ASSIGNMENT_STATUSES,
    ACTIVE_RUN_STATUSES,
)
from processforge_core.work.metadata import WorkMetadataReadPass
from processforge_core.work.projection import (
    ACTIVE_STATUSES,
    WorkProjectionPolicy,
)
from processforge_core.work.record_catalog import WorkRecordCatalogService
from processforge_core.work.records import CurrentWorkService
from processforge_core.work.schema import work_schema
from processforge_core.work.selection import WorkSelectionService
from processforge_core.work.selection_contract import (
    CandidateSet,
    SelectionCandidate,
    SelectionError,
    SelectionRowKey,
    normalize_objective,
    preferred,
)
from processforge_core.work.selection_queries import CanonicalSelectionQueries
from processforge_core.work.selection_schema import selection_schema

_P = "project-uuid"
_ID = re.compile(r"^(?:[a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])$")
_PREFIX = "verify processforge project onboarding"


class SelectionEdge(TypedDict):
    p: str
    r: str
    ordinal: int
    a: str
    cat_valid: int
    cat_local: int
    cur_visible: int
    cur_local: int
    bootstrap: int
    objective_raw: str
    objective_norm: str
    session_id: str
    updated_lex: str
    created_lex: str
    revision: int
    objective_fallback: int
    current_objective_raw: str
    current_objective_norm: str
    current_objective_fallback: int
    created_fallback: int
    updated_fallback: int
    process_fallback: int
    bootstrap_mode: str
    status_fallback: int
    current_status_raw: str
    current_assignment_id: str


class Facts(WorkMetadataReadPass):
    """In-memory source port shared by real legacy readers."""

    def __init__(self, runs, assignments, pending=()):
        super().__init__(Path("."))
        self.run_documents = copy.deepcopy(runs)
        self.assignments = copy.deepcopy(assignments)
        self.pending = set(pending)

    def runs(self):
        for folder, run in sorted(self.run_documents):
            yield Path("runs") / folder / "run.yaml", copy.deepcopy(run)

    def assignment(self, identifier):
        return copy.deepcopy(self.assignments.get(identifier, {}))

    load_assignment = assignment

    def load_run(self, run_id):
        for _folder, run in self.run_documents:
            if run.get("id") == run_id:
                return copy.deepcopy(run)
        return {}

    def assignment_exists(self, identifier):
        return identifier in self.assignments

    def catalog(self):
        service = WorkRecordCatalogService(
            record_reader=lambda: self,
            inventory_factory=lambda: lambda root, loader: self,
            flow_root=lambda: lambda: Path("."),
            document_loader=lambda: lambda path: {},
            identifier_pattern=lambda: _ID,
            intent_reader=lambda: (
                lambda run, task: (
                    ({"operation": "completion"}, None)
                    if (run.get("id"), task.get("id")) in self.pending
                    else (None, None)
                )
            ),
            active_assignment_statuses=lambda: ACTIVE_ASSIGNMENT_STATUSES,
            active_run_statuses=lambda: ACTIVE_RUN_STATUSES,
        )
        return service.records(include_historical=True)

    def current(self):
        return CurrentWorkService(Path("."), work_metadata=lambda: self)


def _insert(connection, table, row):
    columns = ",".join(row)
    placeholders = ",".join("?" for _ in row)
    connection.execute(
        f"INSERT INTO {table}({columns}) VALUES({placeholders})",
        tuple(row.values()),
    )


class ObservedDriver(SQLiteDriver):
    """Test instrumentation; production reader never receives the transport."""

    def _connect(self, *args, **kwargs):
        self.connection = super()._connect(*args, **kwargs)
        return self.connection


@pytest.fixture(autouse=True)
def stores(request, tmp_path_factory, monkeypatch):
    base = request.config.getoption("basetemp")
    root = (Path(base) if base else tmp_path_factory.getbasetemp()).resolve()
    tmp_path = root / uuid4().hex
    tmp_path.mkdir(parents=True)
    monkeypatch.setattr(__import__(__name__, fromlist=["_stores"]), "_stores", [])
    monkeypatch.setattr(
        __import__(__name__, fromlist=["_store_root"]), "_store_root", tmp_path
    )
    yield
    for store in _stores:
        store.close()


_stores: list[FixtureStore] = []
_store_root = Path()


class FixtureStore:
    """Own setup transport and a real Database operation, never emulate SqlSession."""

    def __init__(self):
        self.driver = ObservedDriver()
        self.database = Database(
            self.driver,
            DatabaseTarget(
                _store_root / f"selection-{len(_stores)}.sqlite",
                DatabaseIdentity("a" * 32, "project", _P),
            ),
        )
        SchemaManager().initialize(self.database, (work_schema(), selection_schema()))
        self.setup = sqlite3.connect(self.database.target.path, isolation_level=None)
        self.setup.execute("PRAGMA foreign_keys=ON")
        self.setup.execute("INSERT INTO work_selection_state VALUES(?,1,1)", (_P,))
        self.setup.execute("BEGIN")
        self.operation = None
        self._session = None
        _stores.append(self)

    @property
    def session(self):
        if self.operation is None:
            self.setup.commit()
            self.operation = self.database.read()
            self._session = self.operation.__enter__()
        return self._session

    def end_read(self):
        if self.operation is not None:
            self.operation.__exit__(None, None, None)
            self.operation = None

    def close(self):
        self.end_read()
        self.setup.close()

    def __getattr__(self, name):
        transport = self.driver.connection if self.operation is not None else self.setup
        return getattr(transport, name)


def _new_store():
    return FixtureStore()


def _encode(connection, facts):
    """Encode scalar fixture facts; all production writes remain out of scope."""
    for folder, run in sorted(facts.run_documents):
        run_id = str(run.get("id") or folder)
        run_status = str(run.get("status") or "")
        objective = str(run.get("objective") or "")
        members = run.get("tasks") if isinstance(run.get("tasks"), list) else []
        edges: list[SelectionEdge] = []
        entries = list(enumerate(members)) if members else [(-1, {})]
        for ordinal, member in entries:
            if not isinstance(member, dict):
                continue
            ref = str(member.get("id") or "")
            exists = facts.assignment_exists(ref)
            source = facts.assignment(ref)
            current = (
                source
                if exists
                else {
                    "id": ref,
                    "status": member.get("status"),
                    "objective": run.get("objective"),
                }
            )
            if ordinal == -1:
                current = {}
            a = str(source.get("id") or ref)
            valid = bool(
                ordinal >= 0
                and _ID.fullmatch(run_id)
                and member.get("id")
                and _ID.fullmatch(ref)
                and source
                and _ID.fullmatch(a)
                and str(source.get("run_id") or run_id) == run_id
            )
            current_a = str(current.get("id") or "")
            current_objective = str(current.get("objective") or "")
            bootstrap_mode = (
                "always"
                if current_a == "first-assignment"
                or (exists and current_objective.lower().startswith(_PREFIX))
                else "run"
                if not exists and ordinal >= 0
                else "never"
            )
            session = source.get("session")
            session = session if isinstance(session, dict) else {}
            local_status = str(current.get("status") or "")
            edge = SelectionEdge(
                p=_P,
                r=run_id,
                ordinal=ordinal,
                a=a if ordinal >= 0 else "",
                cat_valid=int(valid),
                cat_local=int(
                    str(source.get("status") or member.get("status") or "")
                    in ACTIVE_ASSIGNMENT_STATUSES
                ),
                cur_visible=1,
                cur_local=int(local_status in ACTIVE_STATUSES),
                bootstrap=int(bootstrap_mode == "always"),
                objective_raw=str(source.get("objective") or ""),
                objective_norm=normalize_objective(str(source.get("objective") or "")),
                session_id=str(session.get("id") or ""),
                updated_lex=str(source.get("updated_at") or ""),
                created_lex=str(source.get("created_at") or ""),
                revision=1,
                objective_fallback=int(not source.get("objective")),
                current_objective_raw=current_objective if exists else "",
                current_objective_norm=normalize_objective(current_objective)
                if exists
                else "",
                current_objective_fallback=int(
                    not exists or not current.get("objective")
                ),
                created_fallback=int(not source.get("created_at")),
                updated_fallback=int(not source.get("updated_at")),
                process_fallback=int(not current.get("process")),
                bootstrap_mode=bootstrap_mode,
                status_fallback=int(not current.get("status")),
                current_status_raw=local_status,
                current_assignment_id=current_a,
            )
            edges.append(edge)
        fixed = [edge for edge in edges if edge["bootstrap_mode"] == "never"]
        run_mode = [edge for edge in edges if edge["bootstrap_mode"] == "run"]
        bootstrap = int(objective.lower().startswith(_PREFIX))
        fixed_local = sum(edge["cur_local"] for edge in fixed)
        run_local = sum(edge["cur_local"] for edge in run_mode)
        _insert(
            connection,
            "work_run_selection",
            dict(
                p=_P,
                r=run_id,
                source_order=folder,
                cat_run=int(run_status in ACTIVE_RUN_STATUSES),
                cur_run=int(run_status in ACTIVE_STATUSES),
                cat_local_n=sum(
                    edge["cat_valid"] * edge["cat_local"] for edge in edges
                ),
                cur_n=len(fixed) + (1 - bootstrap) * len(run_mode),
                cur_local_n=fixed_local + (1 - bootstrap) * run_local,
                revision=1,
                objective_raw=objective,
                objective_norm=normalize_objective(objective),
                created_lex=str(run.get("created_at") or ""),
                updated_lex=str(run.get("updated_at") or ""),
                process_raw=str(run.get("process") or ""),
                status_raw=run_status,
                run_bootstrap=bootstrap,
                cat_objective_fallback_n=sum(
                    edge["cat_valid"] * edge["objective_fallback"] for edge in edges
                ),
                current_objective_fallback_n=sum(
                    edge["current_objective_fallback"] for edge in edges
                ),
                cur_fixed_n=len(fixed),
                cur_run_bootstrap_n=len(run_mode),
                cur_fixed_local_n=fixed_local,
                cur_run_bootstrap_local_n=run_local,
            ),
        )
        for edge in edges:
            _insert(connection, "work_selection_edges", edge)
            if edge["cat_valid"] and (run.get("id"), edge["a"]) in facts.pending:
                _insert(
                    connection,
                    "work_valid_pending_edges",
                    dict(
                        p=_P, r=run_id, ordinal=edge["ordinal"], operation_id="pending"
                    ),
                )
    if facts.assignment_exists("first-assignment"):
        task = facts.assignment("first-assignment")
        _insert(
            connection,
            "work_standalone_selection",
            dict(
                p=_P,
                a="first-assignment",
                objective_raw=str(task.get("objective") or ""),
                status_raw=str(task.get("status") or ""),
                process_raw=str(task.get("process") or ""),
                revision=1,
            ),
        )


def _open(facts):
    connection = _new_store()
    _encode(connection, facts)
    return connection, CanonicalSelectionQueries(connection.session, project_uuid=_P)


def _run(identifier, status="open", tasks=(), objective=" Shared  Objective "):
    return (
        identifier,
        dict(
            id=identifier,
            status=status,
            objective=objective,
            tasks=list(tasks),
            created_at="run-created",
            updated_at="run-updated",
        ),
    )


def _task(identifier, run, status="open", **extra):
    return dict(id=identifier, run_id=run, status=status, **extra)


@pytest.fixture
def mixed():
    return Facts(
        [
            _run(
                "a-run",
                tasks=[
                    {"id": "done"},
                    {"id": "draft"},
                    {"id": "missing", "status": "open"},
                    {"id": "fallback"},
                    {"id": "fallback"},
                    {"id": "mismatch"},
                    {"id": "no-body-id"},
                    "raw-invalid-member",
                    {},
                    {"id": "first-assignment"},
                ],
            ),
            _run("b-run", "completed", [{"id": "closed-open"}]),
            _run("c-run", "completed", [{"id": "terminal"}, {"id": "terminal"}]),
            _run("d-run"),
            _run("e-run", "mystery", [{"id": "unknown"}]),
            _run(
                "f-run",
                tasks=[
                    {"id": "local-bootstrap"},
                    {"id": "missing-bootstrap"},
                    {"id": "empty-local"},
                ],
                objective="Verify ProcessForge project onboarding: fixture",
            ),
            _run("INVALID!", tasks=[{"id": "invalid-run-task"}]),
        ],
        {
            "done": _task("done", "a-run", "done"),
            "draft": _task("draft", "a-run", "draft"),
            "fallback": _task(
                "fallback", "a-run", "", objective="", session={"id": "s"}
            ),
            "mismatch": _task("mismatch", "wrong-run"),
            "no-body-id": dict(run_id="a-run", status="open"),
            "closed-open": _task("closed-open", "b-run"),
            "terminal": _task("terminal", "c-run", "completed"),
            "unknown": _task("unknown", "e-run", "mystery"),
            "local-bootstrap": _task(
                "local-bootstrap",
                "f-run",
                objective="Verify ProcessForge project onboarding local",
            ),
            "empty-local": _task("empty-local", "f-run", objective=""),
            "invalid-run-task": _task("invalid-run-task", "INVALID!"),
            "first-assignment": dict(id="first-assignment", status="open"),
            "orphan": _task("orphan", "absent"),
        },
        pending=[("c-run", "terminal"), ("a-run", "draft")],
    )


def _catalog_tuple(row):
    return (
        row["run_id"],
        row["assignment_id"],
        row["objective"],
        row["session_id"],
        row["updated_at"],
        row["created_at"],
        row["pending_completion"],
    )


def _candidate_tuple(row):
    return (
        row.key.run_id,
        row.assignment_id,
        row.objective,
        row.session_id,
        row.updated_lex,
        row.created_lex,
        row.pending_completion,
    )


def _current_tuple(row):
    return row["run_id"], row["assignment_id"], row["objective"]


def test_catalog_and_current_match_actual_legacy_services(mixed):
    connection, queries = _open(mixed)
    try:
        expected = [row for row in mixed.catalog() if row["active"]]
        assert [_candidate_tuple(row) for row in queries.catalog_active().rows] == [
            _catalog_tuple(row) for row in expected
        ]
        current = queries.current_active().rows
        assert [
            (row.key.run_id, row.assignment_id, row.objective) for row in current
        ] == [_current_tuple(row) for row in mixed.current().active_items()]
        assert not any(
            row.assignment_id == "closed-open" for row in queries.catalog_active().rows
        )
        assert any(row.assignment_id == "closed-open" for row in current)
        assert [
            row.key.ordinal
            for row in queries.catalog_active().rows
            if row.assignment_id == "terminal"
        ] == [0, 1]
        assert (
            sum(row.assignment_id == "draft" for row in queries.catalog_active().rows)
            == 1
        )
        assert any(row.key.ordinal == -1 for row in current)
        assert any(row.assignment_id == "" and row.key.ordinal >= 0 for row in current)
        assert any(row.assignment_id == "empty-local" for row in current)
        assert not any(
            row.assignment_id
            in {"first-assignment", "missing-bootstrap", "local-bootstrap", "orphan"}
            for row in current
        )
    finally:
        connection.close()


def test_objective_history_matches_real_catalog_and_current(mixed):
    connection, queries = _open(mixed)
    try:
        for objective in (
            "shared\tobjective",
            "VERIFY ProcessForge project onboarding: fixture",
            "absent",
            "   ",
        ):
            normalized = normalize_objective(objective)
            expected = [
                row
                for row in mixed.catalog()
                if not row["active"]
                and normalize_objective(row["objective"]) == normalized
            ]
            assert [
                _candidate_tuple(row)
                for row in queries.objective_history(
                    objective=objective, model="catalog"
                ).rows
            ] == [_catalog_tuple(row) for row in expected]
            expected_current = mixed.current().find_by_objective(objective)[
                "historical"
            ]
            assert [
                (row.key.run_id, row.assignment_id, row.objective)
                for row in queries.objective_history(
                    objective=objective, model="current"
                ).rows
            ] == [_current_tuple(row) for row in expected_current]
        # Unknown states are catalog history, but current 'other' is omitted.
        assert any(
            row.assignment_id == "unknown"
            for row in queries.objective_history(
                objective="shared objective", model="catalog"
            ).rows
        )
        assert not any(
            row.assignment_id == "unknown"
            for row in queries.objective_history(
                objective="shared objective", model="current"
            ).rows
        )
    finally:
        connection.close()


def test_duplicate_membership_exact_lookup_and_run_ambiguity(mixed):
    connection, queries = _open(mixed)
    try:
        keys = queries.run_choice(run_id="c-run")
        assert [key.ordinal for key in keys] == [0, 1]
        assert queries.exact_members(run_id="c-run", assignment_id="terminal") == keys
        assert queries.assignment_members(assignment_id="terminal") == keys
        assert queries.assignment_members(assignment_id="orphan") == ()
        assert queries.run_choice(run_id="d-run") == ()
        assert queries.exact_members(run_id="a-run", assignment_id="mismatch") == ()
        assert queries.assignment_members(assignment_id="absent") == ()
        # Exercise the original selector's duplicate-membership decision.
        service = WorkSelectionService(
            bound_selection=lambda session: None,
            valid_selector=lambda value: True,
            records=lambda **kwargs: mixed.catalog(),
            prefer=lambda rows, session: rows[0],
            load_run=lambda identifier: {},
            load_assignment=lambda identifier: {},
        )
        with pytest.raises(ValueError, match="assignment_choice_required"):
            service.select(run_id="c-run")
    finally:
        connection.close()


def test_assignment_lookup_uses_source_order_not_run_id():
    facts = Facts(
        [
            ("z-folder", dict(id="a-run", status="open", tasks=[{"id": "shared"}])),
            (
                "a-folder",
                dict(
                    id="z-run",
                    status="open",
                    tasks=[{"id": "shared"}, {"id": "shared"}],
                ),
            ),
        ],
        {"shared": dict(id="shared", status="open")},
    )
    connection, queries = _open(facts)
    try:
        assert [
            (key.run_id, key.ordinal)
            for key in queries.assignment_members(assignment_id="shared")
        ] == [("z-run", 0), ("z-run", 1), ("a-run", 0)]
    finally:
        connection.close()


def _edit_run(connection, identifier, *, status=None, objective=None, updated=None):
    """Atomic test fixture mutation; never offered as a product writer."""
    connection.end_read()
    connection.execute("BEGIN")
    if status is not None:
        connection.execute(
            "UPDATE work_run_selection SET status_raw=?,cat_run=?,cur_run=?,"
            "revision=revision+1 WHERE p=? AND r=?",
            (
                status,
                int(status in ACTIVE_RUN_STATUSES),
                int(status in ACTIVE_STATUSES),
                _P,
                identifier,
            ),
        )
    if objective is not None:
        bootstrap = int(objective.lower().startswith(_PREFIX))
        connection.execute(
            "UPDATE work_run_selection SET objective_raw=?,objective_norm=?,"
            "run_bootstrap=?,cur_n=cur_fixed_n+(1-?)*cur_run_bootstrap_n,"
            "cur_local_n=cur_fixed_local_n+(1-?)*cur_run_bootstrap_local_n,"
            "revision=revision+1 WHERE p=? AND r=?",
            (
                objective,
                normalize_objective(objective),
                bootstrap,
                bootstrap,
                bootstrap,
                _P,
                identifier,
            ),
        )
    if updated is not None:
        connection.execute(
            "UPDATE work_run_selection SET updated_lex=?,revision=revision+1 WHERE p=? AND r=?",
            (updated, _P, identifier),
        )
    connection.execute(
        "UPDATE work_selection_state SET catalog_revision=catalog_revision+1 WHERE p=?",
        (_P,),
    )
    connection.execute("COMMIT")
    return CanonicalSelectionQueries(connection.session, project_uuid=_P)


def test_run_fallback_and_bootstrap_flips_do_not_rewrite_edges():
    facts = Facts(
        [
            _run(
                "r",
                tasks=[
                    {"id": "fallback"},
                    {"id": "missing", "status": "open"},
                    {"id": "fixed"},
                    {"id": "local"},
                ],
            ),
        ],
        {
            "fallback": _task("fallback", "r", "", objective=""),
            "fixed": _task("fixed", "r", "done", objective="fixed"),
            "local": _task("local", "r", "open", objective="local"),
        },
    )
    connection, queries = _open(facts)
    before = connection.execute(
        "SELECT * FROM work_selection_edges ORDER BY ordinal"
    ).fetchall()
    try:
        queries = _edit_run(
            connection,
            "r",
            status="completed",
            objective="new objective",
            updated="new-time",
        )
        rows = queries.current_active()
        assert rows.catalog_revision == 2
        assert [row.assignment_id for row in rows.rows] == ["missing", "local"]
        assert rows.rows[0].objective == "new objective"
        assert rows.rows[0].updated_lex == "new-time"
        assert not queries.catalog_active().rows
        assert [
            row.assignment_id
            for row in queries.objective_history(
                objective="new objective", model="current"
            ).rows
        ] == ["fallback"]
        queries = _edit_run(
            connection, "r", status="open", objective=_PREFIX + " changed"
        )
        assert [row.assignment_id for row in queries.current_active().rows] == [
            "fallback",
            "fixed",
            "local",
        ]
        assert [row.assignment_id for row in queries.catalog_active().rows] == ["local"]
        queries = _edit_run(connection, "r", objective="normal")
        assert [row.assignment_id for row in queries.current_active().rows] == [
            "fallback",
            "missing",
            "fixed",
            "local",
        ]
        assert (
            connection.execute(
                "SELECT * FROM work_selection_edges ORDER BY ordinal"
            ).fetchall()
            == before
        )
    finally:
        connection.close()


def test_preferred_objective_session_and_first_traversal_ties():
    def candidate(run, ordinal, assignment, updated, created, session):
        return SelectionCandidate(
            SelectionRowKey(_P, run, ordinal),
            assignment,
            run,
            "Straße\t WORK",
            session,
            updated,
            created,
            False,
        )

    first = candidate("a", 0, "same", "z", "c", "")
    duplicate = replace(first, key=replace(first.key, ordinal=1))
    bound = candidate("b", 0, "bound", "a", "c", "session")
    rows = (first, duplicate, bound)
    service = WorkSelectionService(
        bound_selection=lambda value: None,
        valid_selector=lambda value: True,
        records=lambda **kwargs: [],
        prefer=lambda values, value: None,
        load_run=lambda value: {},
        load_assignment=lambda value: {},
    )
    for session in ("", "session", "unknown"):
        expected = service.preferred_record(
            [
                dict(
                    updated_at=row.updated_lex,
                    created_at=row.created_lex,
                    assignment_id=row.assignment_id,
                    session_id=row.session_id,
                    occurrence=i,
                )
                for i, row in enumerate(rows)
            ],
            session,
        )
        assert expected is not None
        assert preferred(rows, session_id=session) is rows[expected["occurrence"]]
    assert preferred((), session_id="") is None
    assert preferred(rows, session_id="") is first
    assert first is not None
    assert normalize_objective(
        first.objective
    ) == WorkProjectionPolicy().normalize_objective("STRASSE work")


def test_current_active_objective_uses_first_traversal_not_preferred():
    facts = Facts(
        [
            _run("a-run", tasks=[{"id": "a"}]),
            _run("z-run", tasks=[{"id": "z"}]),
        ],
        {
            "a": _task("a", "a-run", updated_at="a", objective="match"),
            "z": _task("z", "z-run", updated_at="z", objective="match"),
        },
    )
    connection, queries = _open(facts)
    try:
        matches = tuple(
            row
            for row in queries.current_active().rows
            if normalize_objective(row.objective) == "match"
        )
        assert (
            matches[0].assignment_id
            == facts.current().find_by_objective("match")["active"]["assignment_id"]
        )
        selected = preferred(queries.catalog_active().rows, session_id="")
        assert selected is not None
        assert selected.assignment_id == "z"
    finally:
        connection.close()


def test_constructor_is_cold_and_session_owns_snapshot(monkeypatch):
    connection = _new_store()
    session = connection.session
    statements: list[str] = []
    connection.set_trace_callback(statements.append)

    def no_connection(*args, **kwargs):
        raise AssertionError("reader must reuse the supplied session")

    monkeypatch.setattr(connection.driver, "_connect", no_connection)
    queries = CanonicalSelectionQueries(session, project_uuid=_P)
    assert statements == []
    assert queries.catalog_active() == CandidateSet(1, ())
    assert connection.in_transaction
    connection.end_read()
    with pytest.raises(SelectionError, match="selection_store_unavailable"):
        queries.catalog_active()
    with pytest.raises(SelectionError, match="selection_input_invalid"):
        CanonicalSelectionQueries(connection.setup, project_uuid=_P)


@pytest.mark.parametrize(
    "operation",
    [
        lambda q: q.catalog_active(),
        lambda q: q.current_active(),
        lambda q: q.exact_members(run_id="r", assignment_id="a"),
        lambda q: q.run_choice(run_id="r"),
        lambda q: q.assignment_members(assignment_id="a"),
        lambda q: q.objective_history(objective="x", model="catalog"),
    ],
)
def test_each_entry_point_rechecks_session_lifetime(operation):
    connection, queries = _open(Facts([], {}))
    connection.end_read()
    try:
        with pytest.raises(SelectionError, match="selection_store_unavailable"):
            operation(queries)
    finally:
        connection.close()


@pytest.mark.parametrize(
    "mutation,code",
    [
        (
            "UPDATE work_selection_state SET coverage_complete=0",
            "selection_coverage_incomplete",
        ),
        ("DELETE FROM work_selection_state", "selection_coverage_incomplete"),
        ("DELETE FROM pf_schema_versions", "selection_schema_unsupported"),
        (
            "UPDATE pf_schema_versions SET checksum='wrong'",
            "selection_schema_unsupported",
        ),
        ("DROP INDEX we_cat", "selection_store_unavailable"),
    ],
)
def test_incomplete_or_unregistered_canonical_state_refuses(mutation, code):
    connection = _new_store()
    _encode(connection, Facts([_run("r", tasks=[{"id": "a"}])], {"a": _task("a", "r")}))
    connection.execute(mutation)
    try:
        with pytest.raises(SelectionError, match=code):
            CanonicalSelectionQueries(
                connection.session, project_uuid=_P
            ).catalog_active()
        assert connection.in_transaction
    finally:
        connection.close()


def test_all_queries_are_read_only_and_do_not_own_transaction(mixed):
    connection, queries = _open(mixed)
    before = connection.total_changes
    statements: list[str] = []
    connection.set_trace_callback(statements.append)
    try:
        queries.catalog_active()
        queries.current_active()
        queries.exact_members(run_id="a-run", assignment_id="fallback")
        queries.run_choice(run_id="a-run")
        queries.assignment_members(assignment_id="fallback")
        queries.objective_history(objective="shared objective", model="catalog")
        queries.objective_history(objective="shared objective", model="current")
        assert connection.total_changes == before
        assert connection.in_transaction
        assert all(sql.lstrip().upper().startswith("SELECT") for sql in statements)
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("DELETE FROM work_run_selection")
    finally:
        connection.close()


def test_host_read_denial_fails_without_bypassing_authority():
    connection, queries = _open(Facts([], {}))

    def authorize(action, table, column, database, trigger):
        if action == sqlite3.SQLITE_READ and table == "work_selection_state":
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    connection.set_authorizer(authorize)
    try:
        with pytest.raises(SelectionError, match="selection_store_unavailable"):
            queries.catalog_active()
        assert connection.in_transaction
    finally:
        connection.close()


def test_session_thread_boundary_and_detached_immutable_results(mixed):
    connection, queries = _open(mixed)
    result = queries.catalog_active()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with pytest.raises(SelectionError, match="selection_store_unavailable"):
            pool.submit(queries.catalog_active).result()
    assert queries.catalog_active() == result
    connection.end_read()
    assert result.rows
    with pytest.raises(FrozenInstanceError):
        result.rows[0].assignment_id = "changed"
    assert result.rows[0].assignment_id != "changed"


def test_reads_inside_authorized_repository_transaction():
    store = _new_store()
    with store.database.transaction() as session:
        session.execute(
            SqlStatement("UPDATE work_selection_state SET catalog_revision=2")
        )
        queries = CanonicalSelectionQueries(session, project_uuid=_P)
        assert queries.catalog_active() == CandidateSet(2, ())
    with store.database.read() as session:
        assert CanonicalSelectionQueries(
            session, project_uuid=_P
        ).current_active() == CandidateSet(2, ())


@pytest.mark.parametrize("value", [None, 1, True, [], {}, "bad\x00value", "\ud800"])
def test_malformed_text_is_typed_error(value):
    with pytest.raises(SelectionError, match="selection_input_invalid"):
        normalize_objective(value)


@pytest.mark.parametrize("selector", ["", "../run", "BAD", "a_b"])
def test_invalid_selector_rejected_before_db_access(selector):
    connection = _new_store()
    queries = CanonicalSelectionQueries(connection.session, project_uuid=_P)
    connection.end_read()
    with pytest.raises(SelectionError, match="invalid_work_selector"):
        queries.run_choice(run_id=selector)


def test_project_partition_and_candidate_validation(mixed):
    connection, queries = _open(mixed)
    try:
        foreign = CanonicalSelectionQueries(connection.session, project_uuid="other")
        with pytest.raises(SelectionError, match="selection_coverage_incomplete"):
            foreign.catalog_active()
        with pytest.raises(SelectionError, match="selection_input_invalid"):
            queries.objective_history(objective="x", model="unknown")
        with pytest.raises(SelectionError):
            CandidateSet(True, ())
        with pytest.raises(SelectionError):
            SelectionRowKey(_P, "r", True)
        with pytest.raises(SelectionError):
            preferred(cast(tuple[SelectionCandidate, ...], []), session_id="")
    finally:
        connection.close()


def test_invalid_pending_membership_fails_closed():
    connection = _new_store()
    _encode(connection, Facts([_run("r", tasks=[{"id": "missing"}])], {}))
    _insert(
        connection,
        "work_valid_pending_edges",
        dict(p=_P, r="r", ordinal=0, operation_id="invalid-pending"),
    )
    try:
        with pytest.raises(SelectionError, match="selection_invariant_failed"):
            CanonicalSelectionQueries(
                connection.session, project_uuid=_P
            ).catalog_active()
    finally:
        connection.close()


def _vm_steps(connection, operation):
    steps = 0

    def progress():
        nonlocal steps
        steps += 1
        return 0

    connection.set_progress_handler(progress, 1)
    try:
        result = operation()
    finally:
        connection.set_progress_handler(None, 0)
    return steps, result


def _history_fixture(n, *, open_looking=False, many_edges=False):
    runs = [
        _run(
            f"h-{i:05d}",
            "completed",
            [{"id": f"a-{i:05d}"}],
            objective=f"unrelated {i}",
        )
        for i in range(n)
    ]
    assignments = {
        f"a-{i:05d}": _task(
            f"a-{i:05d}", f"h-{i:05d}", "open" if open_looking else "completed"
        )
        for i in range(n)
    }
    if many_edges:
        runs = [
            _run(
                "history",
                "completed",
                [{"id": f"a-{i:05d}"} for i in range(n)],
                objective="unrelated",
            )
        ]
        for task in assignments.values():
            task["run_id"] = "history"
    runs += [
        _run("live", tasks=[{"id": "live-task"}], objective="needle"),
        _run("pending", "completed", [{"id": "pending-task"}], objective="needle"),
    ]
    assignments.update(
        {
            "live-task": _task("live-task", "live"),
            "pending-task": _task("pending-task", "pending", "completed"),
        }
    )
    return Facts(runs, assignments, pending=[("pending", "pending-task")])


@pytest.mark.parametrize("many_edges", [False, True])
def test_active_queries_bound_visited_work_at_4096_4097(many_edges):
    measurements = []
    for n in (0, 4096, 4097):
        connection, queries = _open(_history_fixture(n, many_edges=many_edges))
        try:
            catalog_steps, catalog = _vm_steps(connection, queries.catalog_active)
            current_steps, current = _vm_steps(connection, queries.current_active)
            assert len(catalog.rows) == 2
            assert len(current.rows) == 1
            measurements.append((catalog_steps, current_steps))
        finally:
            connection.close()
    # Small indexed seeks may gain B-tree levels. A history scan adds tens
    # of thousands of opcodes and must fail these generous allowances.
    for position in (0, 1):
        assert measurements[1][position] <= measurements[0][position] + 1500
        assert measurements[2][position] <= measurements[0][position] + 1500
        assert abs(measurements[2][position] - measurements[1][position]) < 500


def test_closed_runs_open_assignments_separate_active_output_cost():
    connection, queries = _open(_history_fixture(4097, open_looking=True))
    try:
        steps, catalog = _vm_steps(connection, queries.catalog_active)
        current_steps, current = _vm_steps(connection, queries.current_active)
        assert len(catalog.rows) == 2
        assert len(current.rows) == 4098  # Actual current OR semantics.
        assert steps < 5000
        assert current_steps > steps
    finally:
        connection.close()


def test_historical_objective_does_not_scan_unrelated_history():
    costs = []
    for n in (0, 4096, 4097):
        facts = _history_fixture(n)
        # terminal pending remains active catalog, but historical current.
        connection, queries = _open(facts)
        try:
            for model in ("catalog", "current"):
                steps, result = _vm_steps(
                    connection,
                    lambda: queries.objective_history(objective="needle", model=model),
                )
                assert len(result.rows) == (0 if model == "catalog" else 1)
                costs.append(steps)
        finally:
            connection.close()
    assert costs[2] <= costs[0] + 1500
    assert costs[4] <= costs[0] + 1500
    assert costs[3] <= costs[1] + 1500
    assert costs[5] <= costs[1] + 1500


def test_catalog_active_output_has_no_4096_cap():
    facts = _history_fixture(4097, open_looking=True)
    for folder, run in facts.run_documents:
        if folder.startswith("h-"):
            run["status"] = "open"
    connection, queries = _open(facts)
    try:
        assert len(queries.catalog_active().rows) == 4099
        assert len(queries.current_active().rows) == 4098
    finally:
        connection.close()


def test_run_choice_visits_two_members_not_full_large_run():
    costs = []
    for n in (2, 4096, 4097):
        connection, queries = _open(_history_fixture(n, many_edges=True))
        try:
            steps, keys = _vm_steps(
                connection, lambda: queries.run_choice(run_id="history")
            )
            assert [key.ordinal for key in keys] == [0, 1]
            costs.append(steps)
        finally:
            connection.close()
    assert costs[1] <= costs[0] + 500
    assert costs[2] <= costs[0] + 500


def test_schema_descriptor_is_immutable_and_contains_final_indexes():
    schema = selection_schema()
    assert schema.namespace == "work_selection" and schema.version == 1
    assert schema == selection_schema()
    connection = _new_store()
    try:
        indexes = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
        }
        assert {
            "wr_cat",
            "wr_cur_all",
            "wr_cur_local",
            "we_assignment",
            "we_cat",
            "we_cur_mode",
            "we_cur_local_mode",
            "we_valid",
            "we_objective",
            "we_session",
            "we_cat_objective_local",
            "we_cat_objective_fallback",
            "wr_cat_objective_fallback",
            "we_current_objective_local",
            "we_current_objective_fallback",
            "wr_current_objective_fallback",
            "wp_operation",
        } <= indexes
        assert "we_cur" not in indexes and "we_cur_local" not in indexes
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        connection.close()
