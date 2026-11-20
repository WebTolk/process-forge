"""Differential selection semantics and bounded work with real SQLite VM steps."""

from __future__ import annotations

import json
import random
import sqlite3
from dataclasses import replace

import pytest

from processforge_core.work.mutation_model import MemberChange, MutationError
from processforge_core.work.selection_contract import normalize_objective
from processforge_core.work.selection_queries import CanonicalSelectionQueries
from tests.work.test_canonical_selection_queries import Facts
from tests.work.test_work_repository import DELETE, Harness, P


@pytest.fixture
def h(request):
    from pathlib import Path
    from uuid import uuid4

    root = Path(request.config.getoption("basetemp")) / uuid4().hex
    root.mkdir(parents=True)
    return Harness(root)


def oracle(harness):
    runs, assignments = [], {}
    for row in harness.read(
        "SELECT * FROM work_entities ORDER BY source_order,entity_id"
    ):
        data = json.loads(row["payload"])
        if row["kind"] == "assignment":
            assignments[row["entity_id"]] = data
        else:
            data["tasks"] = [
                json.loads(m["member_payload"])
                for m in harness.read(
                    "SELECT member_payload FROM work_members WHERE run_id=? ORDER BY ordinal",
                    (row["entity_id"],),
                )
            ]
            runs.append((row["entity_id"], data))
    return Facts(runs, assignments)


def assert_legacy_equal(harness):
    facts = oracle(harness)
    # The caller owns the read transaction and the real SqlSession capability.
    with harness.db.read() as sql:
        queries = CanonicalSelectionQueries(sql, project_uuid=P)
        cat = queries.catalog_active().rows
        expected = [r for r in facts.catalog() if r["active"]]
        assert [
            (
                r.key.run_id,
                r.assignment_id,
                r.objective,
                r.session_id,
                r.created_lex,
                r.updated_lex,
            )
            for r in cat
        ] == [
            (
                r["run_id"],
                r["assignment_id"],
                r["objective"],
                r["session_id"],
                r["created_at"],
                r["updated_at"],
            )
            for r in expected
        ]
        current = queries.current_active().rows
        assert [(r.key.run_id, r.assignment_id, r.objective) for r in current] == [
            (r["run_id"], r["assignment_id"], r["objective"])
            for r in facts.current().active_items()
        ]
        for objective in (
            "Run",
            "",
            "local",
            "verify processforge project onboarding: X",
        ):
            normalized = normalize_objective(objective)
            expected = [
                r
                for r in facts.catalog()
                if not r["active"] and normalize_objective(r["objective"]) == normalized
            ]
            actual = queries.objective_history(
                objective=objective, model="catalog"
            ).rows
            assert [(r.key.run_id, r.assignment_id, r.objective) for r in actual] == [
                (r["run_id"], r["assignment_id"], r["objective"]) for r in expected
            ]
            actual = queries.objective_history(
                objective=objective, model="current"
            ).rows
            expected = facts.current().find_by_objective(objective)["historical"]
            assert [(r.key.run_id, r.assignment_id, r.objective) for r in actual] == [
                (r["run_id"], r["assignment_id"], r["objective"]) for r in expected
            ]
    # Independent recount is test-only. Ordinary mutation uses signed deltas.
    for run in harness.read("SELECT * FROM work_run_selection"):
        edges = harness.read(
            "SELECT * FROM work_selection_edges WHERE r=?", (run["r"],)
        )
        fixed = [
            e for e in edges if e["cur_visible"] and e["bootstrap_mode"] == "never"
        ]
        dynamic = [
            e for e in edges if e["cur_visible"] and e["bootstrap_mode"] == "run"
        ]
        assert run["cat_local_n"] == sum(e["cat_valid"] * e["cat_local"] for e in edges)
        assert run["cur_fixed_n"] == len(fixed)
        assert run["cur_run_bootstrap_n"] == len(dynamic)
        assert run["cur_fixed_local_n"] == sum(e["cur_local"] for e in fixed)
        assert run["cur_run_bootstrap_local_n"] == sum(e["cur_local"] for e in dynamic)
        assert run["cur_n"] == len(fixed) + (1 - run["run_bootstrap"]) * len(dynamic)
        assert run["cat_objective_fallback_n"] == sum(
            e["cat_valid"] * e["objective_fallback"] for e in edges
        )
        assert run["current_objective_fallback_n"] == sum(
            e["cur_visible"] * e["current_objective_fallback"] for e in edges
        )


@pytest.mark.parametrize(
    "run_status", ["draft", "open", "completed", "unknown", "blocked"]
)
@pytest.mark.parametrize(
    "task_status",
    [
        "ready",
        "pending",
        "debugging",
        "ready_for_review",
        "open",
        "completed",
        "unknown",
        "",
    ],
)
def test_status_sets_and_fallbacks_differential(h, run_status, task_status):
    edits = [
        (
            "run",
            "r",
            {
                "id": "r",
                "status": run_status,
                "objective": "Run",
                "updated_at": "Z",
                "created_at": "A",
                "process": "p",
            },
        ),
        (
            "assignment",
            "a",
            {
                "id": "a",
                "status": task_status,
                "objective": "",
                "created_at": "B",
                "session": {"id": "s"},
            },
        ),
        ("assignment", "empty", {}),
        ("assignment", "orphan", {"id": "orphan", "status": "open"}),
    ]
    members: tuple[tuple[str, int, object], ...] = (
        ("r", 0, {"id": "a", "status": "open"}),
        ("r", 3, {"id": "a"}),
        ("r", 8, {"id": "empty"}),
        ("r", 9, {"id": "missing", "status": "open"}),
        ("r", 12, {}),
        ("r", 15, "opaque"),
    )
    h.repo.apply(h.plan(edits, members=members))
    assert_legacy_equal(h)


def test_bootstrap_empty_missing_synthetic_and_nondict_rows(h):
    h.repo.apply(
        h.plan(
            [
                (
                    "run",
                    "r",
                    {
                        "id": "r",
                        "status": "open",
                        "objective": "verify processforge project onboarding: X",
                    },
                ),
                ("run", "empty-run", {"id": "empty-run", "status": "open"}),
                ("run", "opaque-run", {"id": "opaque-run", "status": "open"}),
                ("assignment", "empty", {}),
                (
                    "assignment",
                    "local",
                    {
                        "id": "local",
                        "objective": "verify processforge project onboarding: X",
                    },
                ),
                (
                    "assignment",
                    "first-assignment",
                    {"id": "first-assignment", "status": "open"},
                ),
            ],
            members=(
                ("r", 0, {"id": "missing", "status": "open"}),
                ("r", 1, {"id": "empty"}),
                ("r", 2, {"id": "local"}),
                ("r", 3, {"id": "first-assignment"}),
                ("opaque-run", 0, False),
            ),
        )
    )
    assert_legacy_equal(h)
    edges_before = h.read("SELECT * FROM work_selection_edges WHERE r='r'")
    h.repo.apply(
        h.plan([("run", "r", {"id": "r", "status": "completed", "objective": "Run"})])
    )
    assert h.read("SELECT * FROM work_selection_edges WHERE r='r'") == edges_before
    assert_legacy_equal(h)
    # Last raw non-dict deletion makes a synthetic row; JSON null insertion
    # removes it again but still produces no real current item.
    h.repo.apply(
        h.plan(
            [("run", "opaque-run", {"id": "opaque-run", "status": "open"})],
            members=(("opaque-run", 0, DELETE),),
        )
    )
    assert h.read("SELECT ordinal FROM work_selection_edges WHERE r='opaque-run'") == [
        {"ordinal": -1}
    ]
    assert_legacy_equal(h)
    h.repo.apply(
        h.plan(
            [("run", "opaque-run", {"id": "opaque-run", "status": "open"})],
            members=(("opaque-run", 7, None),),
        )
    )
    assert h.read("SELECT ordinal FROM work_selection_edges WHERE r='opaque-run'") == [
        {"ordinal": 7}
    ]
    assert_legacy_equal(h)


def test_assignment_alias_invalid_run_and_indexed_fanout(h):
    h.repo.apply(
        h.plan(
            [
                ("run", "r1", {"id": "r1", "status": "open", "objective": "Run"}),
                ("run", "r2", {"id": "r2", "status": "open"}),
                ("assignment", "source", {"id": "alias", "status": "open"}),
                (
                    "assignment",
                    "wrong",
                    {"id": "wrong", "run_id": "elsewhere", "status": "open"},
                ),
            ],
            members=(
                ("r1", 0, {"id": "source"}),
                ("r1", 3, {"id": "source"}),
                ("r2", 0, {"id": "source"}),
                ("r1", 5, {"id": "wrong"}),
            ),
        )
    )
    assert_legacy_equal(h)
    h.repo.apply(
        h.plan(
            [
                (
                    "assignment",
                    "source",
                    {"id": "new-alias", "status": "completed", "objective": "local"},
                )
            ]
        )
    )
    assert_legacy_equal(h)
    assert len(h.read("SELECT * FROM work_selection_edges WHERE a='new-alias'")) == 3
    assert any("INDEXED BY work_member_lookup" in s for s in h.driver.statements)
    assert any("INDEXED BY we_assignment" in s for s in h.driver.statements)


def test_randomized_member_assignment_run_arithmetic(h):
    h.seed()
    rng = random.Random(43134)
    for i in range(45):
        if i % 3 == 0:
            status = rng.choice(["open", "draft", "completed", "unknown", "blocked"])
            objective = rng.choice(
                ["Run", "local", "verify processforge project onboarding: X", ""]
            )
            plan = h.plan(
                [("run", "r", {"id": "r", "status": status, "objective": objective})]
            )
        elif i % 3 == 1:
            status = rng.choice(
                ["ready", "open", "pending", "completed", "unknown", ""]
            )
            plan = h.plan(
                [
                    (
                        "assignment",
                        "a",
                        {
                            "id": "a",
                            "status": status,
                            "objective": rng.choice(["", "local"]),
                        },
                    )
                ]
            )
        else:
            ordinal = rng.randrange(5)
            exists = h.read(
                "SELECT ordinal FROM work_members WHERE run_id=? AND ordinal=?",
                ("r", ordinal),
            )
            value = (
                DELETE
                if exists and rng.randrange(2)
                else rng.choice(
                    [{"id": "a"}, {"id": "missing", "status": "open"}, {}, "raw", None]
                )
            )
            plan = h.plan(
                [
                    (
                        "run",
                        "r",
                        json.loads(
                            h.read(
                                "SELECT payload FROM work_entities WHERE kind='run' AND entity_id='r'"
                            )[0]["payload"]
                        ),
                    )
                ],
                members=(("r", ordinal, value),),
            )
        h.repo.apply(plan)
        assert_legacy_equal(h)


def test_before_edge_and_counter_corruption_rollback(h):
    h.seed()
    plan = h.plan([("assignment", "a", {"id": "a", "status": "open"})])
    h.execute("UPDATE work_selection_edges SET current_status_raw='unexpected'")
    before = h.dump()
    with pytest.raises(MutationError, match="selection_invariant_failed"):
        h.repo.apply(plan)
    assert h.dump() == before
    # SQL CHECK can be bypassed by external damage; kernel verifies identities.
    with sqlite3.connect(h.db.target.path) as sql:
        sql.execute("PRAGMA ignore_check_constraints=ON")
        sql.execute("UPDATE work_run_selection SET cur_n=99")
    plan = h.plan([("run", "r", {})])
    with pytest.raises(MutationError, match="selection_invariant_failed"):
        h.repo.apply(plan)


def test_missing_read_revisions_member_history_and_revision_overflow(h):
    h.seed()
    plan = h.plan([("assignment", "a", {"id": "a", "status": "open"})])
    incomplete = replace(
        plan.proof,
        entities=tuple(e for e in plan.proof.entities if e.key.kind != "run"),
    )
    with pytest.raises(MutationError, match="mutation_read_set_incomplete"):
        h.repo.apply(replace(plan, proof=incomplete))
    with pytest.raises(MutationError, match="mutation_read_set_incomplete"):
        replace(plan, members=(MemberChange("r", 0, None),))
    h.execute(
        "UPDATE work_entities SET revision=? WHERE kind='assignment'", (2**63 - 1,)
    )
    plan = h.plan([("assignment", "a", {"id": "a"})])
    before = h.dump()
    with pytest.raises(MutationError, match="mutation_integer_invalid"):
        h.repo.apply(plan)
    assert h.dump() == before


def test_bounded_mutation_vm_steps_as_history_grows(h):
    h.seed()
    observations = []
    for target in (0, 31, 255):
        for _ in range(
            target
            - len(h.read("SELECT * FROM work_history WHERE entity_kind='run'"))
            + 1
        ):
            h.repo.apply(
                h.plan(
                    [("run", "r", {"id": "r", "status": "open", "objective": "Run"})]
                )
            )
        plan = h.plan([("run", "r", {"id": "r", "status": "open", "objective": "Run"})])
        h.reset()
        h.repo.apply(plan)
        observations.append(
            (len(h.driver.statements), h.driver.write_count, h.driver.steps)
        )
        assert not any(
            "SELECT" in s and "work_history" in s for s in h.driver.statements
        )
        assert not any(
            "MAX(" in s.upper() or "COUNT(" in s.upper() for s in h.driver.statements
        )
        assert not any("UPDATE work_selection_edges" in s for s in h.driver.statements)
    assert len({(sql, writes) for sql, writes, _ in observations}) == 1
    assert (
        max(steps for _, _, steps in observations)
        < min(steps for _, _, steps in observations) * 2
    )
    print(
        "W43 bounded history observations (statements,writes,sqlite_vm_steps):",
        observations,
    )
