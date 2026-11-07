"""Behavioral atomicity/replay/CAS tests using real SQLite and threads only."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from uuid import uuid4

import pytest

from processforge_core.database import (
    Database,
    DatabaseError,
    DatabaseIdentity,
    DatabaseTarget,
    SchemaManager,
    SQLiteDriver,
    SqlStatement,
)
from processforge_core.work.mutation_codec import encode
from processforge_core.work.mutation_model import (
    DeliveryDraft,
    Encoded,
    EntityAfter,
    EntityEdit,
    EntityKey,
    EventDraft,
    ExpectedEntity,
    MemberChange,
    MutationError,
    MutationPlan,
    ReadProof,
    StoreBinding,
)
from processforge_core.work.repository import SqlWorkRepository
from processforge_core.work.schema import work_schema
from processforge_core.work.selection_schema import selection_schema

P = "project-uuid"


class ObservedDriver(SQLiteDriver):
    """Observe SQL and inject write/exit failures without a fake SQL engine."""

    def __init__(self):
        self.fail_at = None
        self.fail_commit = False
        self.fail_reads = False
        self.statements = []
        self.write_count = 0
        self.steps = 0
        self.native_commit_failure = False

    def _connect(self, database, *, timeout=5.0, isolation_level="", uri=False):
        driver = self

        class Connection(sqlite3.Connection):
            def commit(self):
                super().commit()
                if driver.native_commit_failure:
                    driver.native_commit_failure = False
                    raise sqlite3.OperationalError("injected lost commit response")

            def set_progress_handler(self, callback, n):
                def count():
                    driver.steps += 1
                    return callback() if driver.steps % n == 0 else 0

                return super().set_progress_handler(count if callback else None, 1)

        return sqlite3.connect(
            database,
            timeout=timeout,
            isolation_level=isolation_level,
            uri=uri,
            factory=Connection,
        )

    @contextmanager
    def open(self, target, *, mode, timeout_ms, deadline=None):
        if mode == "ro" and self.fail_reads:
            raise DatabaseError("database_io_failed")
        driver = self

        class Session:
            def fetch_one(self, statement):
                driver.statements.append(statement.text)
                return sql.fetch_one(statement)

            def stream(self, statement, *, batch_size=256):
                driver.statements.append(statement.text)
                return sql.stream(statement, batch_size=batch_size)

            def execute(self, statement):
                driver.statements.append(statement.text)
                driver.write_count += 1
                if driver.write_count == driver.fail_at:
                    raise DatabaseError("database_io_failed")
                return sql.execute(statement)

            def execute_many(self, statement, values):
                raise AssertionError("unexpected batch writer")

        with super().open(
            target, mode=mode, timeout_ms=timeout_ms, deadline=deadline
        ) as sql:
            yield Session()
        if mode == "rw" and self.fail_commit:
            self.fail_commit = False
            raise DatabaseError("database_io_failed")


class Harness:
    """Explicit disposable initialization, never a production auto initializer."""

    def __init__(self, root: Path):
        self.driver = ObservedDriver()
        self.db = Database(
            self.driver,
            DatabaseTarget(
                root / "store.sqlite3", DatabaseIdentity("a" * 32, "project", P)
            ),
            timeout_ms=1000,
        )
        self.repo = SqlWorkRepository(self.db, StoreBinding(P, "a" * 32, P, 2))
        SchemaManager().initialize(self.db, (work_schema(), selection_schema()))
        with self.db.transaction() as sql:
            sql.execute(
                SqlStatement(
                    "INSERT INTO work_state VALUES(?,1,'sql','ready',2,1,1,'complete',1,'[]',NULL,NULL)",
                    (P,),
                )
            )
            sql.execute(
                SqlStatement("INSERT INTO work_selection_state VALUES(?,1,1)", (P,))
            )
        self.reset()

    def reset(self):
        self.driver.statements.clear()
        self.driver.write_count = 0
        self.driver.steps = 0

    def read(self, query, params=()):
        with self.db.read() as sql:
            with sql.stream(SqlStatement(query, params)) as stream:
                return [dict(zip(r.columns, r.values)) for r in stream]

    def execute(self, query, params=()):
        with self.db.transaction() as sql:
            sql.execute(SqlStatement(query, params))

    def dump(self):
        with sqlite3.connect(self.db.target.path) as sql:
            return tuple(sql.iterdump())

    def plan(
        self,
        edits,
        *,
        members=(),
        key=None,
        op=None,
        events=(),
        deliveries=(),
        read_keys=(),
    ):
        keys = set(read_keys) | {EntityKey(kind, ident) for kind, ident, _ in edits}
        keys.update(
            EntityKey("run", row["run_id"])
            for row in self.read("SELECT run_id FROM work_members")
        )
        # Test planner takes a full current read set for fixture simplicity. The
        # production kernel requires only affected entities plus referenced facts.
        keys.update(
            EntityKey(row["kind"], row["entity_id"])
            for row in self.read("SELECT kind,entity_id FROM work_entities")
        )
        keys.update(
            EntityKey("assignment", row["assignment_ref"])
            for row in self.read(
                "SELECT assignment_ref FROM work_members WHERE assignment_ref<>''"
            )
        )
        keys.update(
            EntityKey("assignment", str(value.get("id") or ""))
            for _, _, value in members
            if isinstance(value, dict) and value.get("id")
        )
        expected = []
        for k in sorted(keys, key=lambda k: (k.kind, k.entity_id)):
            row = self.read(
                "SELECT revision FROM work_entities WHERE kind=? AND entity_id=?",
                (k.kind, k.entity_id),
            )
            expected.append(ExpectedEntity(k, row[0]["revision"] if row else None))
        revision = self.read("SELECT catalog_revision FROM work_state")[0][
            "catalog_revision"
        ]
        return MutationPlan(
            op or uuid4().hex,
            key,
            encode({"request": "unchanged"}),
            encode({"accepted": True}),
            encode({"receipt": "original"}),
            ReadProof(revision, tuple(expected)),
            tuple(
                EntityEdit(
                    EntityAfter(EntityKey(kind, ident), encode(payload), ident),
                    encode({"delta": payload}),
                    "raw time",
                )
                for kind, ident, payload in edits
            ),
            tuple(
                MemberChange(r, ordinal, None if value is DELETE else encode(value))
                for r, ordinal, value in members
            ),
            tuple(events),
            tuple(deliveries),
        )

    def seed(self):
        plan = self.plan(
            [
                ("run", "r", {"id": "r", "status": "open", "objective": "Run"}),
                ("assignment", "a", {"id": "a", "run_id": "r", "status": "ready"}),
            ],
            members=(("r", 0, {"id": "a"}),),
        )
        return self.repo.apply(plan)


DELETE = object()


@pytest.fixture
def h(request):
    base = request.config.getoption("basetemp")
    root = Path(base) / uuid4().hex
    root.mkdir(parents=True)
    return Harness(root)


def test_commit_atomic_rows_receipt_and_keyset(h):
    event = EventDraft("event-1", 7, "updated", encode({"event": 1}))
    draft = DeliveryDraft(
        "step-1", 3, "event", "event-1", 1, encode({"dependencies": []}), "due"
    )
    plan = h.plan(
        [
            ("run", "r", {"status": "open"}),
            ("assignment", "a", {"id": "a", "status": "open"}),
        ],
        members=(("r", 4, {"id": "a"}), ("r", 9, {"id": "a"})),
        key="",
        events=(event,),
        deliveries=(draft,),
    )
    result = h.repo.apply(plan)
    assert result.acceptance == "accepted"
    assert result.receipt.accepted_seq == 1
    assert result.delivery.pending_steps == 1
    assert result.delivery.state == "pending"
    assert h.read("SELECT next_change_seq,catalog_revision FROM work_state") == [
        {"next_change_seq": 5, "catalog_revision": 2}
    ]
    assert [
        row["ordinal"]
        for row in h.read("SELECT ordinal FROM work_members ORDER BY ordinal")
    ] == [4, 9]
    assert len(h.read("SELECT * FROM work_history")) == 2
    assert h.read("SELECT changed_seq FROM work_entities ORDER BY kind") == [
        {"changed_seq": 3},
        {"changed_seq": 2},
    ]
    assert h.read("SELECT change_seq FROM work_events") == [{"change_seq": 4}]
    page = h.repo.history(EntityKey("run", "r"), limit=1)
    assert page.records[0].entity_revision == 1
    assert page.records[0].body.codec == "cj1"
    assert page.next_seq is None
    h.repo.apply(h.plan([("run", "r", {"status": "completed"})]))
    page = h.repo.history(EntityKey("run", "r"), limit=1)
    assert page.next_seq == page.records[0].seq
    assert (
        h.repo.history(EntityKey("run", "r"), after_seq=page.next_seq)
        .records[0]
        .entity_revision
        == 2
    )


def test_replay_precedes_stale_proof_and_returns_original_ids(h):
    plan = h.plan([("run", "r", {"status": "open"})], key="Key")
    accepted = h.repo.apply(plan)
    h.repo.apply(h.plan([("run", "r", {"status": "completed"})]))
    lost = replace(
        plan, operation_id="discarded-tentative-id", receipt=encode({"wrong": "today"})
    )
    replay = h.repo.apply(lost)
    assert replay.receipt == accepted.receipt
    assert replay.acceptance == "replayed"
    assert h.repo.lookup_request("metadata", "Key", plan.request) == replay
    assert h.repo.lookup_operation(plan.operation_id) == replay
    with pytest.raises(MutationError, match="mutation_key_conflict"):
        h.repo.apply(replace(lost, request=encode({"changed": True})))
    assert len(h.read("SELECT * FROM work_operations")) == 2


def test_request_bytes_compared_even_if_stored_hash_matches(h):
    plan = h.plan([("run", "r", {})], key="key")
    h.repo.apply(plan)
    h.execute("UPDATE work_operations SET request_body='{}'")
    with pytest.raises(MutationError, match="mutation_key_conflict"):
        h.repo.apply(plan)


def test_no_key_empty_string_and_operation_identity(h):
    plan = h.plan([("run", "r", {})], key=None)
    accepted = h.repo.apply(plan)
    assert h.repo.apply(plan).receipt == accepted.receipt
    assert h.repo.lookup_request("metadata", None, plan.request) is None
    for key in (None, "", ""):
        update = h.plan([("run", "r", {})], key=key)
        result = h.repo.apply(update)
        assert result.acceptance == (
            "replayed"
            if key == ""
            and len(h.read("SELECT * FROM work_operations")) == 3
            and result.receipt.operation_id != update.operation_id
            else "accepted"
        )
    assert [
        row["client_key"] for row in h.read("SELECT client_key FROM work_operations")
    ].count(None) == 2
    assert len(h.read("SELECT * FROM work_operations")) == 3
    with pytest.raises(MutationError, match="mutation_operation_conflict"):
        h.repo.apply(replace(plan, request=encode({"different": 1})))


def test_frozen_inputs_and_invalid_exact_types(h):
    leaf = {"y": 2}
    source = {"x": [1, leaf]}
    encoded = encode(source)
    leaf["y"] = 9
    assert encoded.body == b'{"x":[1,{"y":2}]}'
    with pytest.raises(FrozenInstanceError):
        setattr(encoded, "body", b"{}")
    with pytest.raises(MutationError):
        invalid_call(Encoded, bytearray(b"{}"))
    with pytest.raises(MutationError):
        Encoded(b"{}", True)
    with pytest.raises(MutationError, match="mutation_codec_unsupported"):
        Encoded(b"{}", 2)
    plan = h.plan([("run", "r", {})])
    for key in (1, True, b"key", "bad\x00", "\ud800"):
        with pytest.raises(MutationError):
            replace(plan, client_key=key)
    with pytest.raises(MutationError):
        replace(plan, entities=list(plan.entities))
    with pytest.raises(MutationError):
        MemberChange("r", True, encode({}))
    with pytest.raises(MutationError):
        replace(plan, entities=plan.entities * 2)


@pytest.mark.parametrize(
    "field,value",
    [
        ("generation", 3),
        ("active_coverage", "unknown"),
        ("readiness", "blocked"),
        ("required_features", '["future"]'),
    ],
)
def test_state_fails_closed_without_implicit_import(h, field, value):
    plan = h.plan([("run", "r", {})])
    h.execute(f"UPDATE work_state SET {field}=?", (value,))
    before = h.dump()
    with pytest.raises(MutationError, match="mutation_state_not_ready"):
        h.repo.apply(plan)
    assert h.dump() == before


def test_revision_catalog_schema_and_coverage_conflicts(h):
    h.seed()
    stale = h.plan([("assignment", "a", {"id": "a", "status": "open"})])
    h.repo.apply(h.plan([("run", "other", {})]))
    with pytest.raises(MutationError, match="mutation_catalog_conflict"):
        h.repo.apply(stale)
    proof = replace(
        stale.proof,
        catalog_revision=h.read("SELECT catalog_revision FROM work_state")[0][
            "catalog_revision"
        ],
        entities=tuple(
            replace(e, revision=77) if e.key == EntityKey("assignment", "a") else e
            for e in stale.proof.entities
        ),
    )
    with pytest.raises(MutationError, match="mutation_revision_conflict"):
        h.repo.apply(replace(stale, proof=proof))
    fresh = h.plan([("run", "r", {})])
    h.execute("UPDATE work_selection_state SET coverage_complete=0")
    with pytest.raises(MutationError, match="mutation_state_not_ready"):
        h.repo.apply(fresh)
    with sqlite3.connect(h.db.target.path) as sql:
        sql.execute("UPDATE pf_schema_versions SET version=2 WHERE namespace='work'")
    with pytest.raises(MutationError, match="mutation_schema_unsupported"):
        h.repo.apply(fresh)


def test_cold_constructor_and_unsupported_capabilities(h):
    path = h.db.target.path.parent / "absent.sqlite3"
    db = Database(
        SQLiteDriver(), DatabaseTarget(path, DatabaseIdentity("a" * 32, "project", P))
    )
    SqlWorkRepository(db, StoreBinding(P, "a" * 32, P, 2))
    assert not path.exists()
    plan = h.plan([("run", "r", {"objects": ["unverified"]})])
    with pytest.raises(MutationError, match="mutation_capability_unsupported"):
        h.repo.apply(plan)
    with pytest.raises(MutationError):
        invalid_call(DeliveryDraft, "s", 0, "immutable_link", "x", 1, encode({}), "")
    h.seed()
    h.execute(
        "INSERT INTO work_health VALUES(?, 'issue','run','r','bad','blocking',?,'open',1)",
        (P, "sha256:" + "0" * 64),
    )
    with pytest.raises(MutationError, match="mutation_capability_unsupported"):
        h.repo.apply(h.plan([("run", "r", {})]))


@pytest.mark.parametrize(
    "column,value", [("next_change_seq", 2**63 - 2), ("catalog_revision", 2**63 - 1)]
)
def test_int64_allocator_overflow_is_atomic(h, column, value):
    h.execute(f"UPDATE work_state SET {column}=?", (value,))
    if column == "catalog_revision":
        h.execute("UPDATE work_selection_state SET catalog_revision=?", (value,))
    plan = h.plan([("run", "r", {})])
    before = h.dump()
    with pytest.raises(MutationError, match="mutation_integer_invalid"):
        h.repo.apply(plan)
    assert h.dump() == before


def test_fault_rollback_at_every_write_statement(h):
    event = EventDraft("e", 0, "update", encode({}))
    draft = DeliveryDraft("d", 0, "event", "e", 1, encode({}), "")
    plan = h.plan(
        [
            ("run", "r", {"status": "open"}),
            ("assignment", "a", {"id": "a", "status": "open"}),
        ],
        members=(("r", 0, {"id": "a"}),),
        events=(event,),
        deliveries=(draft,),
    )
    before = h.dump()
    # Exact write families in this plan are covered, including singleton CAS,
    # operation/entity/history/member/selection/event/outbox/state/catalog.
    for index in range(1, 14):
        h.reset()
        h.driver.fail_at = index
        with pytest.raises(MutationError, match="mutation_outcome_unknown") as error:
            h.repo.apply(plan)
        assert error.value.operation_id == plan.operation_id
        h.driver.fail_at = None
        assert h.dump() == before
    h.reset()
    result = h.repo.apply(plan)
    assert h.driver.write_count == 13
    assert result.acceptance == "accepted"


def test_postcommit_response_loss_recovers_exactly_and_unknown_preserves_id(h):
    plan = h.plan([("run", "r", {})], key="stable")
    h.driver.fail_commit = True
    recovered = h.repo.apply(plan)
    assert recovered.acceptance == "replayed"
    assert recovered.receipt.operation_id == plan.operation_id
    next_plan = h.plan([("run", "r", {"status": "open"})])
    h.driver.fail_commit = True
    h.driver.fail_reads = True
    with pytest.raises(MutationError, match="mutation_outcome_unknown") as error:
        h.repo.apply(next_plan)
    assert error.value.operation_id == next_plan.operation_id
    h.driver.fail_reads = False
    assert h.repo.lookup_operation(next_plan.operation_id) is not None
    assert h.repo.apply(next_plan).acceptance == "replayed"


def invalid_call(constructor, *args):
    """Intentionally invalid runtime inputs bypass static constructor checking."""
    return constructor(*args)


def test_native_commit_exception_after_real_commit_recovers(h):
    plan = h.plan([("run", "r", {})])
    h.driver.native_commit_failure = True
    result = h.repo.apply(plan)
    assert result.acceptance == "replayed"
    assert result.receipt.operation_id == plan.operation_id
    assert len(h.read("SELECT * FROM work_operations")) == 1


def test_standalone_corruption_is_rejected_without_repair(h):
    h.repo.apply(
        h.plan(
            [
                (
                    "assignment",
                    "first-assignment",
                    {"id": "first-assignment", "status": "open"},
                )
            ]
        )
    )
    h.execute("UPDATE work_standalone_selection SET objective_raw='corrupt'")
    plan = h.plan(
        [
            (
                "assignment",
                "first-assignment",
                {"id": "first-assignment", "status": "completed"},
            )
        ]
    )
    before = h.dump()
    with pytest.raises(MutationError, match="selection_invariant_failed"):
        h.repo.apply(plan)
    assert h.dump() == before


@pytest.mark.parametrize(
    "scenario", ["replace_member", "delete_member", "assignment_fanout"]
)
def test_update_delete_rollback_at_each_write(h, scenario):
    h.seed()
    if scenario == "assignment_fanout":
        plan = h.plan([("assignment", "a", {"id": "a", "status": "completed"})])
    else:
        value = (
            DELETE
            if scenario == "delete_member"
            else {"id": "missing", "status": "open"}
        )
        plan = h.plan(
            [("run", "r", {"id": "r", "status": "open"})], members=(("r", 0, value),)
        )
    root = h.db.target.path.parent / "control"
    root.mkdir()
    control = Harness(root)
    control.seed()
    control.reset()
    control.repo.apply(plan)
    writes = control.driver.write_count
    before = h.dump()
    for index in range(1, writes + 1):
        h.reset()
        h.driver.fail_at = index
        with pytest.raises(MutationError, match="mutation_outcome_unknown"):
            h.repo.apply(plan)
        h.driver.fail_at = None
        assert h.dump() == before
    h.reset()
    h.repo.apply(plan)
    assert h.driver.write_count == writes


@pytest.mark.parametrize("collision", ["event", "outbox"])
def test_stable_event_outbox_identity_collision_rolls_back(h, collision):
    event = EventDraft("stable-event", 0, "updated", encode({"v": 1}))
    draft = DeliveryDraft(
        "stable-step", 0, "event", "stable-event", 1, encode({"v": 1}), ""
    )
    h.repo.apply(h.plan([("run", "r", {})], events=(event,), deliveries=(draft,)))
    plan = h.plan(
        [("run", "r", {"status": "open"})],
        events=(replace(event, envelope=encode({"v": 2})),)
        if collision == "event"
        else (),
        deliveries=(replace(draft, payload=encode({"v": 2})),)
        if collision == "outbox"
        else (),
    )
    before = h.dump()
    with pytest.raises(MutationError, match="mutation_outcome_unknown") as error:
        h.repo.apply(plan)
    assert error.value.operation_id == plan.operation_id
    assert h.dump() == before


def test_key_and_catalog_races_use_real_connections(h):
    first = h.plan([("run", "r1", {})], key="race")
    second = h.plan([("run", "r2", {})], key="race")
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(h.repo.apply, (first, second)))
    assert {r.acceptance for r in results} == {"accepted", "replayed"}
    assert results[0].receipt == results[1].receipt
    assert len(h.read("SELECT * FROM work_entities")) == 1
    plans = (h.plan([("run", "r3", {})]), h.plan([("run", "r4", {})]))

    def apply(plan):
        try:
            return h.repo.apply(plan).acceptance
        except MutationError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(apply, plans))
    assert sorted(outcomes) == ["accepted", "mutation_catalog_conflict"]


@pytest.mark.parametrize("mismatch", ["binding", "stored_generation", "project"])
@pytest.mark.parametrize(
    "action",
    [
        "apply",
        "apply_no_key",
        "apply_conflict",
        "lookup",
        "lookup_unknown",
        "lookup_conflict",
        "operation",
        "operation_unknown",
    ],
)
def test_replay_and_lookup_require_current_store_binding(h, mismatch, action):
    plan = h.plan([("run", "r", {"status": "open"})], key="stable")
    h.repo.apply(plan)
    repo = h.repo
    if mismatch == "binding":
        repo = SqlWorkRepository(h.db, StoreBinding(P, "a" * 32, P, 3))
    elif mismatch == "stored_generation":
        # A long-lived repository must observe a later store generation change.
        h.execute("UPDATE work_state SET generation=3")
    else:
        repo = SqlWorkRepository(h.db, StoreBinding("other-project", "a" * 32, P, 2))
    before = h.dump()
    h.reset()
    with pytest.raises(MutationError, match="^mutation_state_not_ready$"):
        if action == "apply":
            repo.apply(plan)
        elif action == "apply_no_key":
            repo.apply(replace(plan, client_key=None))
        elif action == "apply_conflict":
            repo.apply(replace(plan, request=encode({"changed": True})))
        elif action == "lookup":
            repo.lookup_request("metadata", plan.client_key, plan.request)
        elif action == "lookup_unknown":
            repo.lookup_request("metadata", "unknown", plan.request)
        elif action == "lookup_conflict":
            repo.lookup_request("metadata", plan.client_key, encode({"changed": True}))
        elif action == "operation":
            repo.lookup_operation(plan.operation_id)
        else:
            repo.lookup_operation("unknown-operation")
    assert h.driver.write_count == 0
    assert not any("work_operations" in s for s in h.driver.statements)
    assert h.dump() == before


def test_replay_preserves_bytes_and_current_delivery_after_later_revisions(h):
    draft = DeliveryDraft("step", 0, "event", "event", 1, encode({}), "due")
    plan = h.plan([("run", "r", {"status": "open"})], key="stable", deliveries=(draft,))
    accepted = h.repo.apply(plan)
    for status in ("blocked", "completed"):
        h.repo.apply(h.plan([("run", "r", {"status": status})]))
    h.execute("UPDATE work_outbox SET status='applied'")
    h.execute(
        "UPDATE work_operation_state SET revision=2,state='applied',pending_steps=0,next_due_at='' WHERE operation_id=?",
        (plan.operation_id,),
    )
    before = h.dump()
    h.reset()
    replay = h.repo.apply(
        replace(plan, operation_id="unused", receipt=encode({"today": True}))
    )
    assert replay.receipt == accepted.receipt
    assert replay.receipt.receipt.body == plan.receipt.body
    assert replay.delivery.revision == 2
    assert replay.delivery.state == "applied"
    assert h.repo.lookup_request("metadata", "stable", plan.request) == replay
    assert h.repo.lookup_operation(plan.operation_id) == replay
    assert h.repo.lookup_request("metadata", "unknown", plan.request) is None
    assert h.repo.lookup_operation("unknown") is None
    with pytest.raises(MutationError, match="^mutation_key_conflict$"):
        h.repo.lookup_request("metadata", "stable", encode({"different": True}))
    assert h.driver.write_count == 0
    assert not any(
        "work_entities" in s or "work_selection_edges" in s for s in h.driver.statements
    )
    assert h.dump() == before


@pytest.mark.parametrize("key", [None, "stable"])
def test_uncertain_commit_recovery_rejects_changed_generation(h, monkeypatch, key):
    plan = h.plan([("run", "r", {"status": "open"})], key=key)
    original = h.driver.open

    @contextmanager
    def open_then_lose_response(target, *, mode, timeout_ms, deadline=None):
        with original(
            target, mode=mode, timeout_ms=timeout_ms, deadline=deadline
        ) as sql:
            yield sql
        if mode == "rw":
            with sqlite3.connect(target.path) as connection:
                connection.execute("UPDATE work_state SET generation=3")
            raise DatabaseError("database_io_failed")

    monkeypatch.setattr(h.driver, "open", open_then_lose_response)
    with pytest.raises(MutationError, match="^mutation_outcome_unknown$") as error:
        h.repo.apply(plan)
    assert error.value.operation_id == plan.operation_id
    monkeypatch.setattr(h.driver, "open", original)
    assert len(h.read("SELECT * FROM work_operations")) == 1
    assert len(h.read("SELECT * FROM work_entities")) == 1
    assert len(h.read("SELECT * FROM work_history")) == 1
    before = h.dump()
    h.reset()
    with pytest.raises(MutationError, match="^mutation_state_not_ready$"):
        h.repo.apply(plan)
    assert h.driver.write_count == 0
    assert h.dump() == before


@pytest.mark.parametrize("action", ["apply", "request", "operation"])
def test_replay_checks_actual_database_identity_on_each_open(h, action):
    plan = h.plan([("run", "r", {})], key="key")
    h.repo.apply(plan)
    with sqlite3.connect(h.db.target.path) as connection:
        connection.execute("UPDATE pf_store_meta SET store_id=?", ("b" * 32,))
    before = h.dump()
    h.reset()
    if action == "apply":
        with pytest.raises(MutationError, match="^mutation_outcome_unknown$"):
            h.repo.apply(plan)
    else:
        with pytest.raises(DatabaseError, match="^database_foreign$"):
            if action == "request":
                h.repo.lookup_request("metadata", "key", plan.request)
            else:
                h.repo.lookup_operation(plan.operation_id)
    assert h.driver.write_count == 0
    assert h.dump() == before
