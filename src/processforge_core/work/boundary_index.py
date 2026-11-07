"""Bounded metadata lookup on a caller-owned, authorized SqlSession snapshot.

The result is not boundary advice or object authority. The trusted binder must
verify the selected immutable physical object, then use existing route policy
on this exact Run revision. Failure never authorizes looking further backward.
Import, transactional maintenance and physical verification are not implemented.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..database.contracts import SqlSession, SqlStatement
from .boundary_schema import boundary_schema
from .schema import work_schema

NEWEST_SQL = """SELECT run_id,run_revision,timestamp_lex,encounter,
    first_handoff_raw,object_id,object_hash,object_size,object_path
    FROM work_boundary_candidates INDEXED BY work_boundary_newest
    WHERE project_id=? AND generation=? AND eligible=1
    ORDER BY timestamp_lex DESC,encounter ASC LIMIT 1"""


class BoundaryIndexError(ValueError):
    """Missing, stale or inconsistent boundary facts; fail closed."""


@dataclass(frozen=True)
class BoundaryCandidate:
    """Detached metadata, including pinned immutable object identity."""

    project_id: str
    generation: int
    catalog_revision: int
    run_id: str
    run_revision: int
    timestamp_lex: str
    encounter: int
    first_handoff_raw: str
    object_id: str
    object_hash: str
    object_size: int
    object_path: str


@dataclass(frozen=True)
class BoundaryIndex:
    """Cold expected snapshot identity; never opens or commits transactions."""

    project_id: str
    generation: int
    catalog_revision: int

    def __post_init__(self) -> None:
        if (
            type(self.project_id) is not str
            or not self.project_id
            or any(
                type(value) is not int or not 0 <= value < 2**63
                for value in (self.generation, self.catalog_revision)
            )
        ):
            raise BoundaryIndexError("boundary_identity_invalid")

    def newest(self, sql: SqlSession) -> BoundaryCandidate | None:
        """Select once, then validate exact facts without scanning history."""
        for descriptor in (work_schema(), boundary_schema()):
            row = sql.fetch_one(
                SqlStatement(
                    "SELECT version,checksum FROM pf_schema_versions WHERE namespace=?",
                    (descriptor.namespace,),
                )
            )
            if row is None or row.values != (descriptor.version, descriptor.checksum):
                raise BoundaryIndexError("boundary_schema_invalid")
        state = sql.fetch_one(
            SqlStatement(
                """SELECT w.authority,w.readiness,w.active_coverage,w.protocol_version,
                w.required_features,w.generation,w.catalog_revision,
                b.generation AS boundary_generation,
                b.catalog_revision AS boundary_catalog_revision,b.coverage_complete
                FROM work_state w JOIN work_boundary_state b USING(project_id)
                WHERE w.singleton=1 AND w.project_id=?""",
                (self.project_id,),
            )
        )
        if state is None or state.values != (
            "sql",
            "ready",
            "complete",
            1,
            "[]",
            self.generation,
            self.catalog_revision,
            self.generation,
            self.catalog_revision,
            1,
        ):
            raise BoundaryIndexError("boundary_coverage_invalid")
        row = sql.fetch_one(
            SqlStatement(NEWEST_SQL, (self.project_id, self.generation))
        )
        if row is None:
            return None
        r, revision, timestamp, encounter, raw, obj, digest, size, path = row.values
        if (
            any(type(v) is not str for v in (r, timestamp, raw, obj, digest, path))
            or type(revision) is not int
            or type(encounter) is not int
            or type(size) is not int
        ):
            raise BoundaryIndexError("boundary_candidate_invalid")
        # Narrow the detached SqlValue union without coercion of corrupt values.
        assert isinstance(r, str) and isinstance(timestamp, str)
        assert isinstance(raw, str) and isinstance(obj, str)
        assert isinstance(digest, str) and isinstance(path, str)
        assert isinstance(revision, int) and isinstance(encounter, int)
        assert isinstance(size, int)
        if not raw.endswith("-handoff.md"):
            raise BoundaryIndexError("boundary_candidate_invalid")
        entity = sql.fetch_one(
            SqlStatement(
                """SELECT revision,generation,status_raw,deleted,integrity
                FROM work_entities WHERE project_id=? AND kind='run' AND entity_id=?""",
                (self.project_id, r),
            )
        )
        physical = sql.fetch_one(
            SqlStatement(
                """SELECT hash,size,relative_path,immutable,ref_version
                FROM work_file_refs WHERE project_id=? AND object_id=?""",
                (self.project_id, obj),
            )
        )
        if (
            entity is None
            or entity.values != (revision, self.generation, "completed", 0, "valid")
            or physical is None
            or physical.values != (digest, size, path, 1, 1)
        ):
            raise BoundaryIndexError("boundary_integrity_invalid")
        return BoundaryCandidate(
            self.project_id,
            self.generation,
            self.catalog_revision,
            r,
            revision,
            timestamp,
            encounter,
            raw,
            obj,
            digest,
            size,
            path,
        )
