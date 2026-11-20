"""Atomic object associations against real SQLite and W58 object publication."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from processforge_core.database import Database, SQLiteDriver, SqlStatement
from processforge_core.work.compact_model import CompactError, ObjectRef
from processforge_core.work.compact_objects import ProjectObjectStore
from processforge_core.work.mutation_codec import digest, encode
from processforge_core.work.mutation_model import (
    EntityFileUse,
    EntityKey,
    ImmutableLinkDraft,
    MutationError,
    PreparedObject,
    StoreBinding,
)
from tests.work.test_work_repository import Harness, P

RAW = b"\xef\xbb\xbfraw\r\nunchanged\n"
BINDING = StoreBinding(P, "a" * 32, P, 2)


@pytest.mark.parametrize("version", (True, 2))
def test_unknown_or_noninteger_history_descriptor_version_fails_closed(h, version):
    h.repo.apply(plan(h))
    row = h.read("SELECT body FROM work_history")[0]
    doc = json.loads(row["body"])
    doc["version"] = version
    changed = encode(doc)
    h.execute(
        "UPDATE work_history SET body=?,body_hash=?",
        (changed.body.decode(), digest(changed)),
    )
    with pytest.raises(MutationError, match="mutation_history_corrupt"):
        h.repo.lookup_association(EntityKey("run", "r"), 1, "source", 0)


def test_real_directory_redirection_prepare_refused(h):
    root = h.db.target.path.parent
    target = root / "redirected"
    target.mkdir()
    # Windows junction requires no symlink privilege and is an actual reparse point.
    made = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(root / ".pf"), str(target)],
        capture_output=True,
    )
    assert made.returncode == 0
    with pytest.raises(CompactError, match="unsafe_object_path"):
        prepare(h)
    assert h.read("SELECT * FROM work_file_refs") == []


def test_metadata_lookup_preserves_real_body_denial(h):
    proposed = plan(h)
    h.repo.apply(proposed)
    exact = h.repo.lookup_association(EntityKey("run", "r"), 1, "source", 0)

    def deny(path, action):
        raise CompactError("body_denied")

    def sync(path):
        raise AssertionError("read cannot sync")

    store = ProjectObjectStore(
        h.db.target.path.parent, authorize=deny, sync_directory=sync
    )
    with pytest.raises(CompactError, match="body_denied"):
        store.read(exact.ref, maximum_bytes=100)


def test_precommit_failure_rolls_back_all_associations(h, monkeypatch):
    proposed = plan(h)
    before = h.dump()

    class Connection(sqlite3.Connection):
        def commit(self):
            raise sqlite3.OperationalError("injected before real commit")

    def connect(database, *, timeout=5.0, isolation_level="", uri=False):
        return sqlite3.connect(
            database,
            timeout=timeout,
            isolation_level=isolation_level,
            uri=uri,
            factory=Connection,
        )

    monkeypatch.setattr(h.driver, "_connect", connect)
    with pytest.raises(MutationError, match="mutation_outcome_unknown"):
        h.repo.apply(proposed)
    assert h.dump() == before


def test_stale_entity_proof_with_current_catalog_has_no_partial_association(h):
    h.repo.apply(h.plan([("run", "r", {"id": "r"})]))
    proposed = plan(h)
    h.repo.apply(h.plan([("run", "r", {"id": "r", "objective": "changed"})]))
    proposed = replace(
        proposed,
        proof=replace(
            proposed.proof,
            catalog_revision=h.read("SELECT catalog_revision FROM work_state")[0][
                "catalog_revision"
            ],
        ),
    )
    before = h.dump()
    with pytest.raises(MutationError, match="mutation_revision_conflict"):
        h.repo.apply(proposed)
    assert h.dump() == before


@pytest.fixture
def h(tmp_path):
    return Harness(tmp_path)


def prepare(h, raw=RAW, binding=BINDING):
    ref = ObjectRef(
        "sha256", hashlib.sha256(raw).hexdigest(), len(raw), "text/plain", "raw.v1"
    )
    syncs = []

    def authorize(path, action):
        assert path.startswith(".pf/objects/sha256/")
        assert action in ("read", "write_artifact")

    def host_sync(directory):
        # Explicit W58 host assertion fixture, not a physical power-loss proof.
        assert directory.is_dir()
        syncs.append(directory)

    store = ProjectObjectStore(
        h.db.target.path.parent, authorize=authorize, sync_directory=host_sync
    )
    result = PreparedObject.prepare(store, binding, ref, (raw,))
    assert syncs
    return result


def plan(h, *, obj=None, key="key", name="r", role="source", revision=None):
    obj = obj or prepare(h)
    base = h.plan([("run", name, {"id": name, "status": "open"})], key=key)
    expected = next(
        e.revision for e in base.proof.entities if e.key == EntityKey("run", name)
    )
    use = EntityFileUse(
        BINDING,
        EntityKey("run", name),
        revision or (expected or 0) + 1,
        obj.object_id,
        role,
        0,
        obj.ref.codec,
        obj.ref.media_type,
        "logical/source",
        "unreviewed",
    )
    draft = ImmutableLinkDraft(
        base.operation_id + "-link", 0, use, ".pf/artifacts/source.bin", "due"
    )
    return replace(base, objects=(obj,), uses=(use,), immutable_links=(draft,))


def test_atomic_commit_metadata_lookup_and_replay_without_body_io(h, monkeypatch):
    proposed = plan(h)
    h.reset()
    accepted = h.repo.apply(proposed)
    assert accepted.delivery.pending_steps == 1
    assert accepted.delivery.state == "pending"
    assert h.read("SELECT COUNT(*) AS n FROM work_file_refs")[0]["n"] == 1
    physical = h.read("SELECT * FROM work_file_refs")[0]
    assert (physical["media_type"], physical["role"]) == (
        "application/octet-stream",
        "object",
    )
    outbox = h.read("SELECT * FROM work_outbox")[0]
    assert (
        outbox["payload_hash"]
        == "sha256:" + hashlib.sha256(outbox["payload"].encode()).hexdigest()
    )
    assert outbox["target_revision"] == 1 and outbox["target_kind"] == "immutable_link"

    def denied(*args, **kwargs):
        raise AssertionError("metadata/replay attempted body I/O")

    monkeypatch.setattr(ProjectObjectStore, "read", denied)
    monkeypatch.setattr(ProjectObjectStore, "verify", denied)
    monkeypatch.setattr(ProjectObjectStore, "publish", denied)
    h.reset()
    exact = h.repo.lookup_association(EntityKey("run", "r"), 1, "source", 0)
    assert exact.use == proposed.uses[0]
    assert exact.ref == proposed.objects[0].ref
    assert h.repo.lookup_association(EntityKey("run", "r"), 1, "missing", 0) is None
    replay = h.repo.apply(proposed)
    assert replay.receipt == accepted.receipt
    assert replay.acceptance == "replayed"
    assert h.repo.lookup_operation(proposed.operation_id).receipt == accepted.receipt
    assert h.driver.write_count == 0
    assert not any(
        "FROM work_history" in q and "seq>" in q for q in h.driver.statements
    )


def test_one_blob_multiple_roles_entities_revisions_and_later_metadata(h):
    obj = prepare(h)
    first = plan(h, obj=obj)
    other = replace(
        first.uses[0], role="handoff", ordinal=3, media_type="application/octet-stream"
    )
    h.repo.apply(replace(first, uses=(*first.uses, other)))
    h.repo.apply(plan(h, obj=obj, key="second", role="evidence"))
    h.repo.apply(plan(h, obj=obj, key="third", name="s"))
    assert len(h.read("SELECT * FROM work_file_refs")) == 1
    assert len(h.read("SELECT * FROM work_entity_files")) == 4
    assert (h.db.target.path.parent / obj.relative_path).read_bytes() == RAW
    for name, rev, role, ordinal in (
        ("r", 1, "source", 0),
        ("r", 1, "handoff", 3),
        ("r", 2, "evidence", 0),
        ("s", 1, "source", 0),
    ):
        assert h.repo.lookup_association(EntityKey("run", name), rev, role, ordinal)
    h.repo.apply(h.plan([("run", "r", {"objective": "still supported"})]))


@pytest.mark.parametrize(
    "field,value",
    [("project_id", "foreign"), ("store_id", "b" * 32), ("generation", 3)],
)
def test_foreign_prepared_binding_rolls_back(h, field, value):
    obj = prepare(h, binding=replace(BINDING, **{field: value}))
    proposed = plan(h, obj=obj)
    before = h.dump()
    with pytest.raises(MutationError, match="mutation_store_mismatch"):
        h.repo.apply(proposed)
    assert before == h.dump()


@pytest.mark.parametrize(
    "failure",
    (
        "foreign_use",
        "revision",
        "absent_entity",
        "missing_object",
        "draft",
        "unused_object",
        "duplicate_use",
        "duplicate_step",
    ),
)
def test_invalid_association_compositions_have_no_partial_rows(h, failure):
    proposed = plan(h)
    use = proposed.uses[0]
    before = h.dump()
    with pytest.raises(MutationError):
        if failure == "foreign_use":
            proposed = replace(
                proposed, uses=(replace(use, binding=replace(BINDING, generation=99)),)
            )
        elif failure == "revision":
            proposed = replace(proposed, uses=(replace(use, revision=2),))
        elif failure == "absent_entity":
            proposed = replace(
                proposed, uses=(replace(use, key=EntityKey("run", "absent")),)
            )
        elif failure == "missing_object":
            proposed = replace(proposed, uses=(replace(use, object_id="missing"),))
        elif failure == "draft":
            proposed = replace(
                proposed,
                immutable_links=(
                    replace(
                        proposed.immutable_links[0], use=replace(use, role="wrong")
                    ),
                ),
            )
        elif failure == "unused_object":
            proposed = replace(proposed, uses=(), immutable_links=())
        elif failure == "duplicate_use":
            proposed = replace(proposed, uses=(use, use))
        else:
            proposed = replace(proposed, immutable_links=proposed.immutable_links * 2)
        h.repo.apply(proposed)
    assert h.dump() == before


@pytest.mark.parametrize(
    "path",
    (
        "../escape",
        "/absolute",
        "C:/private",
        "a\\b",
        "a//b",
        "a/./b",
        "a/NUL.txt",
        "a/trailing.",
        ".pf/objects/x",
    ),
)
def test_unsafe_targets_refused_before_sql(h, path):
    proposed = plan(h)
    h.reset()
    with pytest.raises(MutationError, match="mutation_target_invalid"):
        replace(proposed.immutable_links[0], target_key=path)
    assert h.driver.write_count == 0


@pytest.mark.parametrize(
    "column,value",
    (
        ("hash", "sha256:" + "0" * 64),
        ("size", 99),
        ("object_id", "foreign"),
        ("media_type", "semantic"),
        ("role", "capsule"),
    ),
)
def test_existing_physical_metadata_conflict_is_atomic(h, column, value):
    first = plan(h)
    h.repo.apply(first)
    # Use a new empty entity to allow an exact existing physical row collision.
    # Foreign-key associations are removed only by this corruption fixture.
    h.execute("DELETE FROM work_entity_files")
    h.execute("UPDATE work_file_refs SET " + column + "=?", (value,))
    second = plan(h, obj=first.objects[0], key="second", name="s")
    before = h.dump()
    with pytest.raises(MutationError, match="mutation_object_conflict"):
        h.repo.apply(second)
    assert h.dump() == before


def test_failure_at_every_dml_family_retains_only_prepared_blob(h, tmp_path):
    h.repo.apply(plan(h))
    writes = h.driver.write_count
    assert writes >= 9
    for n in range(1, writes + 1):
        root = tmp_path / str(n)
        root.mkdir()
        other = Harness(root)
        proposed = plan(other)
        before = other.dump()
        other.reset()
        other.driver.fail_at = n
        with pytest.raises(MutationError, match="mutation_outcome_unknown"):
            other.repo.apply(proposed)
        assert before == other.dump()
        assert (root / proposed.objects[0].relative_path).read_bytes() == RAW


def test_lost_commit_response_exact_recovery_and_current_gate(h):
    proposed = plan(h)
    h.driver.native_commit_failure = True
    accepted = h.repo.apply(proposed)
    assert accepted.acceptance == "replayed"
    assert len(h.read("SELECT * FROM work_entity_files")) == 1
    assert h.repo.lookup_operation(proposed.operation_id).receipt == accepted.receipt
    h.execute("UPDATE work_state SET generation=3")
    with pytest.raises(MutationError, match="mutation_state_not_ready"):
        h.repo.apply(proposed)


def test_concurrent_writers_cas_leaves_no_partial_association(h):
    a = plan(h, key="a")
    b = replace(
        a,
        client_key="b",
        operation_id="different",
        immutable_links=(replace(a.immutable_links[0], step_id="different-link"),),
    )

    def apply(value):
        try:
            return h.repo.apply(value).acceptance
        except MutationError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(apply, (a, b)))
    assert sorted(outcomes) == ["accepted", "mutation_catalog_conflict"]
    assert len(h.read("SELECT * FROM work_entity_files")) == 1
    assert len(h.read("SELECT * FROM work_outbox")) == 1


def test_prepare_failure_and_constructor_cannot_assert_durability(h):
    with pytest.raises(MutationError, match="mutation_prepare_required"):
        PreparedObject()
    ref = ObjectRef(
        "sha256", hashlib.sha256(RAW).hexdigest(), len(RAW), "text/plain", "raw.v1"
    )

    def denied(path, action):
        raise CompactError("denied")

    def unavailable(path):
        raise CompactError("durability_unavailable")

    root = h.db.target.path.parent
    with pytest.raises(CompactError, match="denied"):
        PreparedObject.prepare(
            ProjectObjectStore(root, authorize=denied, sync_directory=unavailable),
            BINDING,
            ref,
            (RAW,),
        )

    def authorize(path, action):
        assert action == "write_artifact"

    with pytest.raises(CompactError, match="durability_unavailable"):
        PreparedObject.prepare(
            ProjectObjectStore(root, authorize=authorize, sync_directory=unavailable),
            BINDING,
            ref,
            (RAW,),
        )
    assert h.read("SELECT * FROM work_file_refs") == []


@pytest.mark.parametrize("growth", (4096, 4097, 100000))
def test_fixed_changed_set_exact_seek_under_history_growth(h, growth):
    h.repo.apply(plan(h))
    h.repo.apply(h.plan([("run", "archive", {"id": "archive"})]))
    archived = h.read("SELECT * FROM work_history WHERE entity_id='archive'")[0]
    # Populate historical corpus directly, using existing schema and real driver.
    with Database(SQLiteDriver(), h.db.target).transaction() as sql:
        for start in range(0, growth, 5000):
            sql.execute_many(
                SqlStatement("INSERT INTO work_history VALUES(?,?,?,?,?,?,?,?,?,?,?)"),
                tuple(
                    (
                        P,
                        10 + i,
                        archived["operation_id"],
                        "run",
                        "archive",
                        2 + i,
                        1,
                        "metadata",
                        archived["body"],
                        archived["body_hash"],
                        "old",
                    )
                    for i in range(start, min(start + 5000, growth))
                ),
            )
        sql.execute(
            SqlStatement("UPDATE work_state SET next_change_seq=?", (growth + 20,))
        )
        sql.execute(
            SqlStatement(
                "UPDATE work_entities SET revision=? WHERE entity_id='archive'",
                (growth + 1,),
            )
        )
    proposed = plan(h, key="next")
    h.reset()
    h.repo.apply(proposed)
    assert h.repo.lookup_association(EntityKey("run", "r"), 2, "source", 0)
    steps = h.driver.steps
    assert steps < 6000
    assert len(h.driver.statements) < 80
    assert not any("FROM work_history" in s for s in h.driver.statements)
    assert not any("OFFSET" in s.upper() for s in h.driver.statements)
    query = "SELECT * FROM work_entity_files WHERE project_id=? AND entity_kind=? AND entity_id=? AND entity_revision=? AND role=? AND ordinal=?"
    explain = h.read("EXPLAIN QUERY PLAN " + query, (P, "run", "r", 2, "source", 0))
    assert all(
        "SEARCH" in r["detail"] and "PRIMARY KEY" in r["detail"] for r in explain
    )
    print(
        {
            "history_rows": growth,
            "steps": steps,
            "sql_count": len(h.driver.statements),
            "sql_bytes": sum(len(s.encode()) for s in h.driver.statements),
            "selected_history_bytes": len(
                h.read(
                    "SELECT body FROM work_history WHERE entity_id='r' AND entity_revision=2"
                )[0]["body"].encode()
            ),
        }
    )
