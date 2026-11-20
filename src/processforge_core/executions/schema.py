"""Code-owned execution@1 DDL. Importing this module performs no I/O."""

import hashlib
import json

from ..database.schema import SchemaDefinition

_DDL = (
    "CREATE TABLE execution_state(singleton INTEGER PRIMARY KEY CHECK(singleton=1),project_id TEXT NOT NULL,generation INTEGER NOT NULL CHECK(generation>=0),authority TEXT NOT NULL CHECK(authority IN ('legacy','sql')),readiness TEXT NOT NULL CHECK(readiness IN ('importing','ready')),active_coverage TEXT NOT NULL CHECK(active_coverage IN ('complete','unknown')),revision INTEGER NOT NULL CHECK(revision>=0),next_history_seq INTEGER NOT NULL CHECK(next_history_seq>=1),migration_id TEXT,plan_checksum TEXT)",
    "CREATE TABLE execution_attempts(project_id TEXT NOT NULL,run_id TEXT NOT NULL,task_id TEXT NOT NULL,attempt INTEGER NOT NULL CHECK(attempt>=1),launch_token TEXT UNIQUE,revision INTEGER NOT NULL CHECK(revision>=1),generation INTEGER NOT NULL CHECK(generation>=0),phase TEXT NOT NULL CHECK(phase IN ('prepared','starting','running','stopping','unresolved','absent')),outcome TEXT CHECK(outcome IN ('completed','failed','timed_out','cancelled','unknown_exit','lost','blocked')),collection TEXT NOT NULL CHECK(collection IN ('pending','collected','failed','refused')),process_json TEXT,history_seq INTEGER UNIQUE CHECK(history_seq>=1),payload_json TEXT NOT NULL,projected_revision INTEGER NOT NULL DEFAULT 0 CHECK(projected_revision>=0 AND projected_revision<=revision),source_path TEXT,source_checksum TEXT,semantic_checksum TEXT,PRIMARY KEY(project_id,run_id,task_id,attempt))",
    "CREATE TABLE execution_heads(project_id TEXT NOT NULL,run_id TEXT NOT NULL,task_id TEXT NOT NULL,latest_attempt INTEGER NOT NULL CHECK(latest_attempt>=1),next_attempt INTEGER NOT NULL CHECK(next_attempt>latest_attempt),projection_dirty INTEGER NOT NULL CHECK(projection_dirty IN (0,1)),PRIMARY KEY(project_id,run_id,task_id),FOREIGN KEY(project_id,run_id,task_id,latest_attempt) REFERENCES execution_attempts(project_id,run_id,task_id,attempt))",
    "CREATE TABLE execution_current(project_id TEXT NOT NULL,run_id TEXT NOT NULL,task_id TEXT NOT NULL,attempt INTEGER NOT NULL,PRIMARY KEY(project_id,run_id,task_id,attempt),UNIQUE(project_id,run_id,task_id),FOREIGN KEY(project_id,run_id,task_id,attempt) REFERENCES execution_attempts(project_id,run_id,task_id,attempt))",
    "CREATE TABLE execution_receipt_admissions(project_id TEXT NOT NULL,run_id TEXT NOT NULL,task_id TEXT NOT NULL,attempt INTEGER NOT NULL,launch_token TEXT NOT NULL,kind TEXT NOT NULL CHECK(kind IN ('process','heartbeat','exit','absence','spawn_failed')),sequence INTEGER NOT NULL CHECK(sequence>=0),checksum TEXT NOT NULL,PRIMARY KEY(project_id,run_id,task_id,attempt,launch_token,kind),FOREIGN KEY(project_id,run_id,task_id,attempt) REFERENCES execution_attempts(project_id,run_id,task_id,attempt))",
    "CREATE INDEX execution_history ON execution_attempts(project_id,history_seq) WHERE history_seq IS NOT NULL",
    "CREATE INDEX execution_projection_dirty ON execution_heads(project_id,run_id,task_id) WHERE projection_dirty=1",
    "CREATE TABLE execution_allocation_floors(project_id TEXT NOT NULL,run_id TEXT NOT NULL,task_id TEXT NOT NULL,next_attempt INTEGER NOT NULL CHECK(next_attempt>=1),PRIMARY KEY(project_id,run_id,task_id))",
)

EXECUTION_SCHEMA = SchemaDefinition(
    namespace="execution",
    version=1,
    statements=_DDL,
    checksum="sha256:"
    + hashlib.sha256(
        json.dumps(
            {"namespace": "execution", "version": 1, "statements": _DDL},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest(),
)
