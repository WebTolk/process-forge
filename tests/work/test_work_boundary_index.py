"""B01 disconnected storage semantics; no migration or route activation."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from processforge_core.database import DatabaseError, SchemaManager, SqlStatement
from processforge_core.work.boundary_advisory import FreshSessionBoundaryReadService
from processforge_core.work.boundary_index import (
    NEWEST_SQL,
    BoundaryIndex,
    BoundaryIndexError,
)
from processforge_core.work.boundary_schema import boundary_schema
from tests.work.test_work_storage_schema import (  # noqa: F401
    _H,
    _P,
    _insert,
    _sample,
    database,
    store_path,
)


@pytest.fixture
def ready(database):  # noqa: F811 - imported pytest fixture
    SchemaManager().apply(database, (boundary_schema(),))
    with database.transaction() as sql:
        sql.execute(
            SqlStatement("""UPDATE work_state SET authority='sql',
            readiness='ready',active_coverage='complete'""")
        )
        sql.execute(
            SqlStatement("INSERT INTO work_boundary_state VALUES(?,0,0,1)", (_P,))
        )
        sql.execute(SqlStatement("UPDATE work_entities SET status_raw='completed'"))
    return database


def candidate(
    sql, run="r", encounter=0, timestamp="", eligible=1, raw="missing-first-handoff.md"
):
    if run != "r":
        _insert(sql, "work_entities", entity_id=run, status_raw="completed")
        _insert(sql, "work_history", seq=encounter + 1, entity_id=run)
    sql.execute(
        SqlStatement(
            """INSERT INTO work_boundary_candidates VALUES(
            ?,?,'run',1,0,?,?,?, ?,?,?,?,?)""",
            (
                _P,
                run,
                timestamp,
                encounter,
                raw,
                eligible,
                "f" if eligible else None,
                _H if eligible else None,
                0 if eligible else None,
                ".pf/objects/fixture" if eligible else None,
            ),
        )
    )


def newest(db):
    with db.read() as sql:
        return BoundaryIndex(_P, 0, 0).newest(sql)


def test_cold_and_coexists(ready):
    assert boundary_schema() == boundary_schema()
    assert SchemaManager().apply(ready, (boundary_schema(),)).state == "ready"
    assert newest(ready) is None
    with pytest.raises(BoundaryIndexError):
        BoundaryIndex(_P, True, 0)


def test_exact_descriptor_checksum():
    descriptor = boundary_schema()
    raw = json.dumps(
        {
            "namespace": descriptor.namespace,
            "version": descriptor.version,
            "statements": descriptor.statements,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    assert descriptor.checksum == "sha256:" + hashlib.sha256(raw).hexdigest()
    assert (
        descriptor.checksum
        == "sha256:5f5cf3e2cddd912530f4764986bc0bb49f30e55a5933e29983a3ec41ba2da5c6"
    )


_RAW_REFERENCES = (
    None,
    "",
    "x",
    "handoff.md",
    "-handoff.md",
    "x-handoff.md",
    "\x00",
    "\x00x-handoff.md",
    "x\x00-handoff.md",
    "x-handoff\x00.md",
    "x-handoff.md\x00",
    "x-handoff.md\x00trailing",
    "x-handoff.md\x00-handoff.md",
    "\x00\x00-handoff.md",
    "ёж🙂-handoff.md",
    "x-handoff.md🙂",
    "x\n-handoff.md",
    "x-handoff.md\n",
    "x-HANDOFF.md",
)


@pytest.mark.parametrize("raw", _RAW_REFERENCES)
def test_sql_raw_suffix_matches_entire_python_string(ready, raw):
    expected = isinstance(raw, str) and raw.endswith("-handoff.md")
    # Every raw legacy fact remains representable without an eligible object.
    with ready.transaction() as sql:
        candidate(sql, eligible=0, raw=raw)
    with ready.read() as sql:
        assert sql.fetch_one(
            SqlStatement("SELECT first_handoff_raw FROM work_boundary_candidates")
        ).values == (raw,)
    assert newest(ready) is None
    promote = SqlStatement(
        """UPDATE work_boundary_candidates SET eligible=1,
        object_id='f',object_hash=?,object_size=0,object_path='.pf/objects/fixture'""",
        (_H,),
    )
    if expected:
        with ready.transaction() as sql:
            sql.execute(promote)
        assert newest(ready).first_handoff_raw == raw
    else:
        with pytest.raises(DatabaseError):
            with ready.transaction() as sql:
                sql.execute(promote)
        assert newest(ready) is None
        with pytest.raises(DatabaseError):
            with ready.transaction() as sql:
                candidate(sql, "invalid", 1, eligible=1, raw=raw)


@pytest.mark.parametrize("raw", ["x-handoff.md\x00trailing", "x-handoff.md\x00"])
def test_reader_rejects_corrupt_suffix_without_backward_fallback(ready, raw):
    with ready.transaction() as sql:
        candidate(sql, timestamp="old")
        candidate(sql, "newest", 1, "zzz")
    # Administrative corruption bypasses CHECK only in this negative fixture.
    with sqlite3.connect(ready.target.path) as connection:
        connection.execute("PRAGMA ignore_check_constraints=ON")
        connection.execute(
            "UPDATE work_boundary_candidates SET first_handoff_raw=? WHERE run_id='newest'",
            (raw,),
        )
    with pytest.raises(BoundaryIndexError, match="boundary_candidate_invalid"):
        newest(ready)


@pytest.mark.parametrize("raw", _RAW_REFERENCES[1:])
def test_real_legacy_raw_suffix_selection(ready, raw):
    root = ready.target.path.parent / "legacy-raw"
    run_path = root / ".pf/runs/r/run.yaml"
    run_path.parent.mkdir(parents=True)
    handoff = "real-handoff.md"
    (root / handoff).write_text("fixture", encoding="utf-8")
    references = [raw, handoff]
    run_path.write_text(
        json.dumps(
            dict(
                id="r",
                status="completed",
                final_artifacts=references,
                process="previous",
                process_execution=dict(
                    allowed_processes=["next"],
                    definition=dict(process_transitions=[dict(to_process="next")]),
                ),
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    first = next(item for item in references if item.endswith("-handoff.md"))
    eligible = int((root / first).is_file())
    with ready.transaction() as sql:
        candidate(sql, raw=first, eligible=eligible)
    actual = FreshSessionBoundaryReadService(root).read({})
    chosen = newest(ready)
    if eligible:
        assert actual["previous_run_id"] == chosen.run_id == "r"
        assert chosen.first_handoff_raw == handoff
    else:
        assert actual == {} and chosen is None
    assert FreshSessionBoundaryReadService(root).read({"governed": True}) == {}


def test_encounter_tie_reverse_lexical_and_no_route_fallback(ready):
    with ready.transaction() as sql:
        candidate(sql, "z-first", 1, "same")
        candidate(sql, "a-later", 2, "same")
    chosen = newest(ready)
    assert chosen.run_id == "z-first"
    # Route data is deliberately absent from storage predicate. Trusted caller
    # returns no advice for this chosen Run rather than selecting a-later.
    with pytest.raises(FrozenInstanceError):
        chosen.run_id = "changed"


@pytest.mark.parametrize(
    "updated,created,expected",
    [
        (None, "created", "created"),
        ("", "created", "created"),
        ("updated", "created", "updated"),
        (0, None, ""),
        ("9", "10", "9"),
    ],
)
def test_import_timestamp_contract(ready, updated, created, expected):
    # Explicit importer obligation, exercising the actual legacy expression.
    with ready.transaction() as sql:
        candidate(sql, timestamp=str(updated or created or ""))
    assert newest(ready).timestamp_lex == expected


def test_unusable_first_reference_never_uses_later_handoff(ready):
    with ready.transaction() as sql:
        candidate(sql, timestamp="old")
        candidate(sql, "new-unusable", 1, "zzz", 0)
    assert newest(ready).run_id == "r"
    with ready.read() as sql:
        row = sql.fetch_one(
            SqlStatement(
                """SELECT first_handoff_raw,object_id FROM work_boundary_candidates
                WHERE run_id='new-unusable'"""
            )
        )
        assert row.values == ("missing-first-handoff.md", None)


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE work_boundary_state SET generation=1",
        "UPDATE work_boundary_state SET catalog_revision=1",
        "UPDATE work_boundary_state SET coverage_complete=0",
        "UPDATE work_state SET generation=1",
        "UPDATE work_state SET catalog_revision=1",
        "UPDATE work_state SET active_coverage='unknown'",
        "UPDATE work_state SET authority='legacy'",
        "UPDATE work_state SET required_features='[\"unknown\"]'",
        "DELETE FROM work_boundary_state",
    ],
)
def test_invariant_fail_closed(ready, mutation):
    with ready.transaction() as sql:
        sql.execute(SqlStatement(mutation))
    with pytest.raises(BoundaryIndexError):
        newest(ready)


def test_descriptor_mismatch(ready):
    # Administrative corruption fixture: ordinary SqlSession forbids metadata DML.
    with sqlite3.connect(ready.target.path) as connection:
        connection.execute(
            "UPDATE pf_schema_versions SET checksum=? WHERE namespace='work_boundary'",
            ("sha256:" + "0" * 64,),
        )
    with pytest.raises(BoundaryIndexError, match="schema"):
        newest(ready)


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE work_entities SET revision=2 WHERE entity_id='z'",
        "UPDATE work_entities SET status_raw='cancelled' WHERE entity_id='z'",
        "UPDATE work_entities SET deleted=1 WHERE entity_id='z'",
        "UPDATE work_file_refs SET size=1 WHERE object_id='f'",
        "UPDATE work_file_refs SET relative_path='corrupt' WHERE object_id='f'",
    ],
)
def test_selected_integrity_failure_does_not_search_backward(ready, mutation):
    with ready.transaction() as sql:
        candidate(sql, timestamp="old")
        candidate(sql, "z", 1, "zzz")
        sql.execute(SqlStatement(mutation))
    with pytest.raises(BoundaryIndexError, match="integrity"):
        newest(ready)


@pytest.mark.parametrize(
    "field,value",
    [
        ("encounter", -1),
        ("encounter", 1.5),
        ("run_revision", 0),
        ("generation", -1),
        ("generation", 1e30),
        ("eligible", 2),
        ("object_size", -1),
        ("object_hash", "bad"),
        ("object_id", "foreign"),
    ],
)
def test_constraints_and_rollback(ready, field, value):
    with ready.transaction() as sql:
        candidate(sql)
    with pytest.raises(DatabaseError):
        with ready.transaction() as sql:
            sql.execute(
                SqlStatement(f"UPDATE work_boundary_candidates SET {field}=?", (value,))
            )
    assert newest(ready).run_revision == 1


def test_exact_revision_fk_and_unique_encounter(ready):
    with ready.transaction() as sql:
        candidate(sql)
    for statement in (
        "UPDATE work_boundary_candidates SET run_revision=2",
        "UPDATE work_boundary_candidates SET run_kind='assignment'",
        "DELETE FROM work_file_refs WHERE object_id='f'",
    ):
        with pytest.raises(DatabaseError):
            with ready.transaction() as sql:
                sql.execute(SqlStatement(statement))
    with pytest.raises(DatabaseError):
        with ready.transaction() as sql:
            candidate(sql, "duplicate-ordinal", 0)


@pytest.mark.parametrize("scenario", ["tie", "no-route", "first-missing"])
def test_real_legacy_fixture_boundary(ready, monkeypatch, scenario):
    root = ready.target.path.parent / "legacy"
    paths = []
    for name in ("z", "a"):
        path = root / ".pf" / "runs" / name / "run.yaml"
        path.parent.mkdir(parents=True)
        handoff = f"{name}-handoff.md"
        (root / handoff).write_text("immutable import fixture", encoding="utf-8")
        missing = scenario == "first-missing" and name == "z"
        timestamp = "same" if scenario == "tie" else ("zzz" if name == "z" else "old")
        run = dict(
            id=name,
            status="completed",
            updated_at=timestamp,
            process="previous",
            final_artifacts=(["absent-handoff.md"] if missing else []) + [handoff],
            process_execution=dict(
                allowed_processes=["next"],
                definition=dict(
                    process_transitions=[]
                    if scenario == "no-route" and name == "z"
                    else [dict(to_process="next")]
                ),
            ),
        )
        path.write_text(json.dumps(run), encoding="utf-8")
        paths.append(path)
        with ready.transaction() as sql:
            candidate(sql, name, len(paths), timestamp, 0 if missing else 1)
    original_glob = Path.glob

    def observed_glob(path, pattern):
        if path == root / ".pf" / "runs" and pattern == "*/run.yaml":
            return iter(paths)  # Observed z-before-a encounter, not sorted IDs.
        return original_glob(path, pattern)

    monkeypatch.setattr(Path, "glob", observed_glob)
    actual = FreshSessionBoundaryReadService(root).read({})
    chosen = newest(ready)
    if scenario == "no-route":
        assert actual == {} and chosen.run_id == "z"
    else:
        assert (
            actual["previous_run_id"]
            == chosen.run_id
            == ("a" if scenario == "first-missing" else "z")
        )
    assert FreshSessionBoundaryReadService(root).read({"governed": True}) == {}


def test_scale_counterexample(ready):
    receipts = []
    with ready.transaction() as sql:
        candidate(sql, timestamp="000-oldest")
    prior = 1
    for count in (4096, 4097, 100000):
        with ready.transaction() as sql:
            for table in ("work_entities", "work_history"):
                rows = []
                for n in range(prior, count):
                    changes = (
                        dict(entity_id=f"r{n}", status_raw="completed")
                        if table == "work_entities"
                        else dict(entity_id=f"r{n}", seq=n + 1)
                    )
                    rows.append(tuple(_sample(table, **changes).values()))
                columns = tuple(_sample(table))
                for offset in range(0, len(rows), 256):
                    sql.execute_many(
                        SqlStatement(
                            f"INSERT INTO {table}({','.join(columns)}) VALUES({','.join('?' for _ in columns)})"
                        ),
                        rows[offset : offset + 256],
                    )
            facts = [(_P, f"r{n}", n) for n in range(prior, count)]
            for offset in range(0, len(facts), 256):
                sql.execute_many(
                    SqlStatement(
                        """INSERT INTO work_boundary_candidates VALUES(
                    ?,?,'run',1,0,'zzz-newer',?,'missing-handoff.md',0,NULL,NULL,NULL,NULL)"""
                    ),
                    facts[offset : offset + 256],
                )
        prior = count
        with ready.read() as sql:
            # Private driver instrumentation is used only in this test; product
            # adapter consumes exclusively the existing public SqlSession API.
            connection = sql._connection
            plan = connection.execute(
                "EXPLAIN QUERY PLAN " + NEWEST_SQL, (_P, 0)
            ).fetchall()
            steps = [0]

            def step():
                steps[0] += 1
                return 0

            connection.set_progress_handler(step, 1)
            assert sql.fetch_one(SqlStatement(NEWEST_SQL, (_P, 0)))["run_id"] == "r"
            indexed_steps = steps[0]
            steps[0] = 0
            baseline = """SELECT run_id,eligible,timestamp_lex,encounter
                FROM work_boundary_candidates WHERE project_id=? ORDER BY run_id"""
            corpus = connection.execute(baseline, (_P,)).fetchall()
            assert len(corpus) == count
            assert (
                max((r for r in corpus if r[1]), key=lambda r: (r[2], -r[3]))[0] == "r"
            )
            baseline_steps = steps[0]
            connection.set_progress_handler(None, 0)
            assert indexed_steps <= 200
            assert baseline_steps > count
            assert all("TEMP B-TREE" not in str(row) for row in plan)
            receipts.append(
                dict(
                    rows=count,
                    indexed_steps=indexed_steps,
                    scan_baseline_steps=baseline_steps,
                    explain=plan,
                )
            )
        assert newest(ready).run_id == "r"
    destination = os.environ.get("W45_EVIDENCE_DIR")
    if destination:
        (Path(destination) / "scale.json").write_text(json.dumps(receipts, indent=2))
