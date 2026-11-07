"""Code-owned work_selection v1 descriptor, never a schema initializer.

Counters belong to the eventual atomic Work mutation repository. In
particular Run metadata edits update one Run and its arithmetic cur counts;
they never rewrite local edge facts. No trigger or partial writer lives here.
"""

from __future__ import annotations

import hashlib
import json

from ..database.schema import SchemaDefinition

__all__ = ("selection_schema",)

_STATEMENTS = (
    """CREATE TABLE work_selection_state(
        p TEXT NOT NULL PRIMARY KEY,
        catalog_revision INTEGER NOT NULL CHECK(catalog_revision>=1),
        coverage_complete INTEGER NOT NULL CHECK(coverage_complete IN(0,1))
    )""",
    """CREATE TABLE work_run_selection(
        p TEXT NOT NULL, r TEXT NOT NULL, source_order TEXT NOT NULL,
        cat_run INTEGER NOT NULL CHECK(cat_run IN(0,1)),
        cur_run INTEGER NOT NULL CHECK(cur_run IN(0,1)),
        cat_local_n INTEGER NOT NULL CHECK(cat_local_n>=0),
        cur_n INTEGER NOT NULL CHECK(cur_n>=0),
        cur_local_n INTEGER NOT NULL CHECK(cur_local_n>=0),
        revision INTEGER NOT NULL CHECK(revision>=1),
        objective_raw TEXT NOT NULL, objective_norm TEXT NOT NULL,
        created_lex TEXT NOT NULL, updated_lex TEXT NOT NULL,
        process_raw TEXT NOT NULL, status_raw TEXT NOT NULL,
        run_bootstrap INTEGER NOT NULL CHECK(run_bootstrap IN(0,1)),
        cat_objective_fallback_n INTEGER NOT NULL
            CHECK(cat_objective_fallback_n>=0),
        current_objective_fallback_n INTEGER NOT NULL
            CHECK(current_objective_fallback_n>=0),
        cur_fixed_n INTEGER NOT NULL CHECK(cur_fixed_n>=0),
        cur_run_bootstrap_n INTEGER NOT NULL CHECK(cur_run_bootstrap_n>=0),
        cur_fixed_local_n INTEGER NOT NULL CHECK(cur_fixed_local_n>=0),
        cur_run_bootstrap_local_n INTEGER NOT NULL
            CHECK(cur_run_bootstrap_local_n>=0),
        PRIMARY KEY(p,r),
        CHECK(cur_n=cur_fixed_n+(1-run_bootstrap)*cur_run_bootstrap_n),
        CHECK(cur_local_n=cur_fixed_local_n
            +(1-run_bootstrap)*cur_run_bootstrap_local_n)
    )""",
    """CREATE INDEX wr_cat ON work_run_selection(
        p,cat_run,source_order,r) WHERE cat_local_n>0""",
    """CREATE INDEX wr_cur_all ON work_run_selection(
        p,cur_run,source_order,r) WHERE cur_n>0""",
    """CREATE INDEX wr_cur_local ON work_run_selection(
        p,cur_run,source_order,r) WHERE cur_local_n>0""",
    """CREATE TABLE work_selection_edges(
        p TEXT NOT NULL, r TEXT NOT NULL,
        ordinal INTEGER NOT NULL CHECK(ordinal>=-1), a TEXT NOT NULL,
        cat_valid INTEGER NOT NULL CHECK(cat_valid IN(0,1)),
        cat_local INTEGER NOT NULL CHECK(cat_local IN(0,1)),
        cur_visible INTEGER NOT NULL CHECK(cur_visible IN(0,1)),
        cur_local INTEGER NOT NULL CHECK(cur_local IN(0,1)),
        bootstrap INTEGER NOT NULL CHECK(bootstrap IN(0,1)),
        objective_raw TEXT NOT NULL, objective_norm TEXT NOT NULL,
        session_id TEXT NOT NULL, updated_lex TEXT NOT NULL,
        created_lex TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK(revision>=1),
        objective_fallback INTEGER NOT NULL CHECK(objective_fallback IN(0,1)),
        current_objective_raw TEXT NOT NULL,
        current_objective_norm TEXT NOT NULL,
        current_objective_fallback INTEGER NOT NULL
            CHECK(current_objective_fallback IN(0,1)),
        created_fallback INTEGER NOT NULL CHECK(created_fallback IN(0,1)),
        updated_fallback INTEGER NOT NULL CHECK(updated_fallback IN(0,1)),
        process_fallback INTEGER NOT NULL CHECK(process_fallback IN(0,1)),
        bootstrap_mode TEXT NOT NULL
            CHECK(bootstrap_mode IN('never','always','run')),
        status_fallback INTEGER NOT NULL CHECK(status_fallback IN(0,1)),
        current_status_raw TEXT NOT NULL,
        current_assignment_id TEXT NOT NULL,
        PRIMARY KEY(p,r,ordinal),
        FOREIGN KEY(p,r) REFERENCES work_run_selection(p,r),
        CHECK(bootstrap=(bootstrap_mode='always')),
        CHECK(ordinal<>-1 OR
            (cat_valid=0 AND a='' AND bootstrap_mode='never'))
    )""",
    """CREATE INDEX we_assignment ON work_selection_edges(p,a,r,ordinal)""",
    """CREATE INDEX we_cat ON work_selection_edges(p,r,ordinal)
        WHERE cat_valid=1 AND cat_local=1""",
    """CREATE INDEX we_cur_mode ON work_selection_edges(
        p,r,bootstrap_mode,ordinal) WHERE cur_visible=1""",
    """CREATE INDEX we_cur_local_mode ON work_selection_edges(
        p,r,bootstrap_mode,ordinal) WHERE cur_visible=1 AND cur_local=1""",
    """CREATE INDEX we_valid ON work_selection_edges(p,r,ordinal)
        WHERE cat_valid=1""",
    """CREATE INDEX we_objective ON work_selection_edges(
        p,objective_norm,r,ordinal)""",
    """CREATE INDEX we_session ON work_selection_edges(
        p,session_id,r,ordinal)""",
    """CREATE INDEX we_cat_objective_local ON work_selection_edges(
        p,objective_norm,r,ordinal)
        WHERE cat_valid=1 AND objective_fallback=0""",
    """CREATE INDEX we_cat_objective_fallback ON work_selection_edges(
        p,r,ordinal) WHERE cat_valid=1 AND objective_fallback=1""",
    """CREATE INDEX wr_cat_objective_fallback ON work_run_selection(
        p,objective_norm,source_order,r) WHERE cat_objective_fallback_n>0""",
    """CREATE INDEX we_current_objective_local ON work_selection_edges(
        p,current_objective_norm,r,ordinal)
        WHERE cur_visible=1 AND current_objective_fallback=0""",
    """CREATE INDEX we_current_objective_fallback ON work_selection_edges(
        p,r,ordinal) WHERE cur_visible=1 AND current_objective_fallback=1""",
    """CREATE INDEX wr_current_objective_fallback ON work_run_selection(
        p,objective_norm,source_order,r)
        WHERE current_objective_fallback_n>0""",
    """CREATE TABLE work_valid_pending_edges(
        p TEXT NOT NULL, r TEXT NOT NULL, ordinal INTEGER NOT NULL,
        operation_id TEXT NOT NULL, PRIMARY KEY(p,r,ordinal),
        FOREIGN KEY(p,r,ordinal)
            REFERENCES work_selection_edges(p,r,ordinal)
    )""",
    """CREATE INDEX wp_operation ON work_valid_pending_edges(
        p,operation_id,r,ordinal)""",
    """CREATE TABLE work_standalone_selection(
        p TEXT NOT NULL, a TEXT NOT NULL CHECK(a='first-assignment'),
        objective_raw TEXT NOT NULL, status_raw TEXT NOT NULL,
        process_raw TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK(revision>=1),
        PRIMARY KEY(p,a)
    )""",
)


def selection_schema() -> SchemaDefinition:
    """Return the existing immutable descriptor with its existing hash formula."""
    definition = {
        "namespace": "work_selection",
        "version": 1,
        "statements": _STATEMENTS,
    }
    raw = json.dumps(
        definition,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return SchemaDefinition(
        "work_selection",
        1,
        _STATEMENTS,
        "sha256:" + hashlib.sha256(raw).hexdigest(),
    )
