"""Disconnected project-local boundary facts; registration is administrative."""

from __future__ import annotations

import hashlib
import json

from ..database.schema import SchemaDefinition

# TEXT substr stops at NUL; BLOB suffix comparison observes the entire raw value.
_STATEMENTS = (
    """CREATE TABLE work_boundary_state(
        project_id TEXT NOT NULL PRIMARY KEY CHECK(typeof(project_id)='text'),
        generation INTEGER NOT NULL CHECK(typeof(generation)='integer' AND generation>=0),
        catalog_revision INTEGER NOT NULL CHECK(typeof(catalog_revision)='integer' AND catalog_revision>=0),
        coverage_complete INTEGER NOT NULL CHECK(typeof(coverage_complete)='integer' AND coverage_complete IN(0,1)),
        FOREIGN KEY(project_id) REFERENCES work_state(project_id)
    ) WITHOUT ROWID""",
    """CREATE TABLE work_boundary_candidates(
        project_id TEXT NOT NULL CHECK(typeof(project_id)='text'),
        run_id TEXT NOT NULL CHECK(typeof(run_id)='text'),
        run_kind TEXT NOT NULL DEFAULT 'run' CHECK(run_kind='run'),
        run_revision INTEGER NOT NULL CHECK(typeof(run_revision)='integer' AND run_revision>=1),
        generation INTEGER NOT NULL CHECK(typeof(generation)='integer' AND generation>=0),
        timestamp_lex TEXT NOT NULL CHECK(typeof(timestamp_lex)='text'),
        encounter INTEGER NOT NULL CHECK(typeof(encounter)='integer' AND encounter>=0),
        first_handoff_raw TEXT CHECK(first_handoff_raw IS NULL OR typeof(first_handoff_raw)='text'),
        eligible INTEGER NOT NULL CHECK(typeof(eligible)='integer' AND eligible IN(0,1)),
        object_id TEXT,
        object_hash TEXT CHECK(object_hash IS NULL OR (typeof(object_hash)='text' AND length(object_hash)=71 AND length(CAST(object_hash AS BLOB))=71 AND substr(object_hash,1,7)='sha256:' AND substr(object_hash,8) NOT GLOB '*[^0-9a-f]*')),
        object_size INTEGER CHECK(object_size IS NULL OR (typeof(object_size)='integer' AND object_size>=0)),
        object_path TEXT CHECK(object_path IS NULL OR typeof(object_path)='text'),
        PRIMARY KEY(project_id,run_id),
        UNIQUE(project_id,generation,encounter),
        FOREIGN KEY(project_id) REFERENCES work_boundary_state(project_id),
        FOREIGN KEY(project_id,run_kind,run_id,run_revision)
            REFERENCES work_history(project_id,entity_kind,entity_id,entity_revision),
        FOREIGN KEY(project_id,object_id) REFERENCES work_file_refs(project_id,object_id),
        CHECK((eligible=0 AND object_id IS NULL AND object_hash IS NULL AND object_size IS NULL AND object_path IS NULL)
           OR (eligible=1 AND typeof(object_id)='text' AND object_hash IS NOT NULL AND object_size IS NOT NULL AND object_path IS NOT NULL AND first_handoff_raw IS NOT NULL AND length(CAST(first_handoff_raw AS BLOB))>=11 AND substr(CAST(first_handoff_raw AS BLOB),-11)=CAST('-handoff.md' AS BLOB)))
    ) WITHOUT ROWID""",
    """CREATE INDEX work_boundary_newest ON work_boundary_candidates(
        project_id,generation,timestamp_lex DESC,encounter ASC) WHERE eligible=1""",
)


def boundary_schema() -> SchemaDefinition:
    """Return work_boundary@1 with the standard canonical descriptor hash."""
    raw = json.dumps(
        {"namespace": "work_boundary", "version": 1, "statements": _STATEMENTS},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return SchemaDefinition(
        "work_boundary", 1, _STATEMENTS, "sha256:" + hashlib.sha256(raw).hexdigest()
    )
