"""Mode-neutral Work storage descriptors; never initialize or activate a store.

DDL supplies structural constraints, not a mutation protocol. Canonical codecs,
CAS, sequence allocation, immutable receipts/history and atomic relation updates
belong to the future transaction-owned repository. Selection remains its own
unchanged namespace. Project/store binding is checked by host composition.
"""

from __future__ import annotations

import hashlib
import json

from ..database.schema import SchemaDefinition

__all__ = ("work_schema", "work_migration_schema")

_WORK_STATEMENTS = (
    """CREATE TABLE work_state(
        project_id TEXT NOT NULL,
        singleton INTEGER NOT NULL CHECK(typeof(singleton)='integer' AND singleton=1),
        authority TEXT NOT NULL CHECK(authority IN('legacy','sql')),
        readiness TEXT NOT NULL CHECK(readiness IN('importing','ready','blocked')),
        generation INTEGER NOT NULL CHECK(typeof(generation)='integer' AND generation>=0),
        catalog_revision INTEGER NOT NULL CHECK(typeof(catalog_revision)='integer' AND catalog_revision>=0),
        next_change_seq INTEGER NOT NULL CHECK(typeof(next_change_seq)='integer' AND next_change_seq>=1),
        active_coverage TEXT NOT NULL CHECK(active_coverage IN('complete','unknown')),
        protocol_version INTEGER NOT NULL CHECK(typeof(protocol_version)='integer' AND protocol_version=1),
        required_features TEXT NOT NULL,
        migration_id TEXT,
        plan_hash TEXT CHECK(plan_hash IS NULL OR (typeof(plan_hash)='text' AND length(plan_hash)=71 AND length(CAST(plan_hash AS BLOB))=71 AND substr(plan_hash,1,7)='sha256:' AND substr(plan_hash,8) NOT GLOB '*[^0-9a-f]*')),
        PRIMARY KEY(singleton),
        UNIQUE(project_id)
    ) WITHOUT ROWID""",
    """CREATE TABLE work_entities(
        project_id TEXT NOT NULL,
        kind TEXT NOT NULL CHECK(kind IN('run','assignment','continuation')),
        entity_id TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK(typeof(revision)='integer' AND revision>=1),
        generation INTEGER NOT NULL CHECK(typeof(generation)='integer' AND generation>=0),
        payload_version INTEGER NOT NULL CHECK(typeof(payload_version)='integer' AND payload_version>=1),
        payload TEXT NOT NULL,
        payload_hash TEXT NOT NULL CHECK(typeof(payload_hash)='text' AND length(payload_hash)=71 AND length(CAST(payload_hash AS BLOB))=71 AND substr(payload_hash,1,7)='sha256:' AND substr(payload_hash,8) NOT GLOB '*[^0-9a-f]*'),
        changed_seq INTEGER NOT NULL CHECK(typeof(changed_seq)='integer' AND changed_seq>=1),
        source_order TEXT NOT NULL,
        integrity TEXT NOT NULL CHECK(integrity IN('valid','placeholder','orphan','invalid')),
        source_ref TEXT,
        status_raw TEXT NOT NULL,
        objective_raw TEXT NOT NULL,
        objective_normalized TEXT NOT NULL,
        created_lex TEXT NOT NULL,
        updated_lex TEXT NOT NULL,
        process_ref TEXT NOT NULL,
        context_ref TEXT NOT NULL,
        session_id TEXT NOT NULL,
        deleted INTEGER NOT NULL CHECK(typeof(deleted)='integer' AND deleted IN(0,1)),
        PRIMARY KEY(project_id,kind,entity_id),
        FOREIGN KEY(project_id) REFERENCES work_state(project_id)
    ) WITHOUT ROWID""",
    """CREATE TABLE work_members(
        project_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        run_kind TEXT NOT NULL DEFAULT 'run' CHECK(run_kind='run'),
        ordinal INTEGER NOT NULL CHECK(typeof(ordinal)='integer' AND ordinal>=0),
        assignment_ref TEXT NOT NULL,
        member_status TEXT NOT NULL,
        member_payload TEXT NOT NULL,
        PRIMARY KEY(project_id,run_id,ordinal),
        FOREIGN KEY(project_id,run_kind,run_id) REFERENCES work_entities(project_id,kind,entity_id),
        FOREIGN KEY(project_id) REFERENCES work_state(project_id)
    ) WITHOUT ROWID""",
    """CREATE TABLE work_operations(
        project_id TEXT NOT NULL,
        operation_id TEXT NOT NULL,
        operation_kind TEXT NOT NULL,
        client_key TEXT,
        request_version INTEGER NOT NULL CHECK(typeof(request_version)='integer' AND request_version>=1),
        request_hash TEXT NOT NULL CHECK(typeof(request_hash)='text' AND length(request_hash)=71 AND length(CAST(request_hash AS BLOB))=71 AND substr(request_hash,1,7)='sha256:' AND substr(request_hash,8) NOT GLOB '*[^0-9a-f]*'),
        request_body TEXT NOT NULL,
        accepted_version INTEGER NOT NULL CHECK(typeof(accepted_version)='integer' AND accepted_version>=1),
        accepted_hash TEXT NOT NULL CHECK(typeof(accepted_hash)='text' AND length(accepted_hash)=71 AND length(CAST(accepted_hash AS BLOB))=71 AND substr(accepted_hash,1,7)='sha256:' AND substr(accepted_hash,8) NOT GLOB '*[^0-9a-f]*'),
        accepted_body TEXT NOT NULL,
        receipt_version INTEGER NOT NULL CHECK(typeof(receipt_version)='integer' AND receipt_version>=1),
        receipt TEXT NOT NULL,
        receipt_hash TEXT NOT NULL CHECK(typeof(receipt_hash)='text' AND length(receipt_hash)=71 AND length(CAST(receipt_hash AS BLOB))=71 AND substr(receipt_hash,1,7)='sha256:' AND substr(receipt_hash,8) NOT GLOB '*[^0-9a-f]*'),
        accepted_seq INTEGER NOT NULL CHECK(typeof(accepted_seq)='integer' AND accepted_seq>=1),
        origin TEXT NOT NULL CHECK(origin IN('client','internal','legacy_import')),
        PRIMARY KEY(operation_id),
        UNIQUE(project_id,operation_id),
        FOREIGN KEY(project_id) REFERENCES work_state(project_id)
    ) WITHOUT ROWID""",
    """CREATE TABLE work_history(
        project_id TEXT NOT NULL,
        seq INTEGER NOT NULL CHECK(typeof(seq)='integer' AND seq>=1),
        operation_id TEXT NOT NULL,
        entity_kind TEXT NOT NULL CHECK(entity_kind IN('run','assignment','continuation')),
        entity_id TEXT NOT NULL,
        entity_revision INTEGER NOT NULL CHECK(typeof(entity_revision)='integer' AND entity_revision>=1),
        record_version INTEGER NOT NULL CHECK(typeof(record_version)='integer' AND record_version>=1),
        history_kind TEXT NOT NULL,
        body TEXT NOT NULL,
        body_hash TEXT NOT NULL CHECK(typeof(body_hash)='text' AND length(body_hash)=71 AND length(CAST(body_hash AS BLOB))=71 AND substr(body_hash,1,7)='sha256:' AND substr(body_hash,8) NOT GLOB '*[^0-9a-f]*'),
        occurred_at TEXT NOT NULL,
        PRIMARY KEY(seq),
        UNIQUE(project_id,entity_kind,entity_id,entity_revision),
        FOREIGN KEY(project_id,operation_id) REFERENCES work_operations(project_id,operation_id),
        FOREIGN KEY(project_id,entity_kind,entity_id) REFERENCES work_entities(project_id,kind,entity_id),
        FOREIGN KEY(project_id) REFERENCES work_state(project_id)
    ) WITHOUT ROWID""",
    """CREATE TABLE work_operation_state(
        project_id TEXT NOT NULL,
        operation_id TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK(typeof(revision)='integer' AND revision>=1),
        state TEXT NOT NULL CHECK(state IN('pending','applied','blocked')),
        next_due_at TEXT NOT NULL,
        last_error_code TEXT NOT NULL,
        pending_steps INTEGER NOT NULL CHECK(typeof(pending_steps)='integer' AND pending_steps>=0),
        PRIMARY KEY(operation_id),
        FOREIGN KEY(project_id,operation_id) REFERENCES work_operations(project_id,operation_id),
        CHECK(state<>'applied' OR pending_steps=0),
        FOREIGN KEY(project_id) REFERENCES work_state(project_id)
    ) WITHOUT ROWID""",
    """CREATE TABLE work_events(
        project_id TEXT NOT NULL,
        event_id TEXT NOT NULL,
        operation_id TEXT NOT NULL,
        ordinal INTEGER NOT NULL CHECK(typeof(ordinal)='integer' AND ordinal>=0),
        event_type TEXT NOT NULL,
        event_version INTEGER NOT NULL CHECK(typeof(event_version)='integer' AND event_version>=1),
        canonical_envelope TEXT NOT NULL,
        envelope_hash TEXT NOT NULL CHECK(typeof(envelope_hash)='text' AND length(envelope_hash)=71 AND length(CAST(envelope_hash AS BLOB))=71 AND substr(envelope_hash,1,7)='sha256:' AND substr(envelope_hash,8) NOT GLOB '*[^0-9a-f]*'),
        change_seq INTEGER NOT NULL CHECK(typeof(change_seq)='integer' AND change_seq>=1),
        PRIMARY KEY(event_id),
        UNIQUE(project_id,operation_id,ordinal),
        FOREIGN KEY(project_id,operation_id) REFERENCES work_operations(project_id,operation_id),
        FOREIGN KEY(project_id) REFERENCES work_state(project_id)
    ) WITHOUT ROWID""",
    """CREATE TABLE work_outbox(
        project_id TEXT NOT NULL,
        step_id TEXT NOT NULL,
        operation_id TEXT NOT NULL,
        ordinal INTEGER NOT NULL CHECK(typeof(ordinal)='integer' AND ordinal>=0),
        target_kind TEXT NOT NULL CHECK(target_kind IN('immutable_link','yaml','derived','event','dispatch')),
        target_key TEXT NOT NULL,
        target_revision INTEGER NOT NULL CHECK(typeof(target_revision)='integer' AND target_revision>=0),
        payload_version INTEGER NOT NULL CHECK(typeof(payload_version)='integer' AND payload_version>=1),
        payload TEXT NOT NULL,
        payload_hash TEXT NOT NULL CHECK(typeof(payload_hash)='text' AND length(payload_hash)=71 AND length(CAST(payload_hash AS BLOB))=71 AND substr(payload_hash,1,7)='sha256:' AND substr(payload_hash,8) NOT GLOB '*[^0-9a-f]*'),
        status TEXT NOT NULL CHECK(status IN('pending','claimed','applied','blocked','superseded')),
        next_due_at TEXT NOT NULL,
        claim_epoch INTEGER NOT NULL CHECK(typeof(claim_epoch)='integer' AND claim_epoch>=0),
        attempt_count INTEGER NOT NULL CHECK(typeof(attempt_count)='integer' AND attempt_count>=0),
        last_error_code TEXT NOT NULL,
        PRIMARY KEY(step_id),
        UNIQUE(project_id,operation_id,ordinal),
        FOREIGN KEY(project_id,operation_id) REFERENCES work_operations(project_id,operation_id),
        FOREIGN KEY(project_id) REFERENCES work_state(project_id)
    ) WITHOUT ROWID""",
    """CREATE TABLE work_file_refs(
        project_id TEXT NOT NULL,
        object_id TEXT NOT NULL,
        hash TEXT NOT NULL CHECK(typeof(hash)='text' AND length(hash)=71 AND length(CAST(hash AS BLOB))=71 AND substr(hash,1,7)='sha256:' AND substr(hash,8) NOT GLOB '*[^0-9a-f]*'),
        size INTEGER NOT NULL CHECK(typeof(size)='integer' AND size>=0),
        media_type TEXT NOT NULL,
        ref_version INTEGER NOT NULL CHECK(typeof(ref_version)='integer' AND ref_version=1),
        relative_path TEXT NOT NULL,
        role TEXT NOT NULL,
        immutable INTEGER NOT NULL CHECK(typeof(immutable)='integer' AND immutable=1),
        PRIMARY KEY(object_id),
        UNIQUE(project_id,object_id),
        UNIQUE(project_id,relative_path),
        FOREIGN KEY(project_id) REFERENCES work_state(project_id)
    ) WITHOUT ROWID""",
    """CREATE TABLE work_entity_files(
        project_id TEXT NOT NULL,
        entity_kind TEXT NOT NULL CHECK(entity_kind IN('run','assignment','continuation')),
        entity_id TEXT NOT NULL,
        entity_revision INTEGER NOT NULL CHECK(typeof(entity_revision)='integer' AND entity_revision>=1),
        object_id TEXT NOT NULL,
        role TEXT NOT NULL,
        ordinal INTEGER NOT NULL CHECK(typeof(ordinal)='integer' AND ordinal>=0),
        PRIMARY KEY(project_id,entity_kind,entity_id,entity_revision,role,ordinal),
        FOREIGN KEY(project_id,entity_kind,entity_id,entity_revision) REFERENCES work_history(project_id,entity_kind,entity_id,entity_revision),
        FOREIGN KEY(project_id,object_id) REFERENCES work_file_refs(project_id,object_id),
        FOREIGN KEY(project_id) REFERENCES work_state(project_id)
    ) WITHOUT ROWID""",
    """CREATE TABLE work_bindings(
        project_id TEXT NOT NULL,
        binding_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        assignment_id TEXT NOT NULL,
        context_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        run_kind TEXT NOT NULL DEFAULT 'run' CHECK(run_kind='run'),
        assignment_kind TEXT NOT NULL DEFAULT 'assignment' CHECK(assignment_kind='assignment'),
        revision INTEGER NOT NULL CHECK(typeof(revision)='integer' AND revision>=1),
        generation INTEGER NOT NULL CHECK(typeof(generation)='integer' AND generation>=0),
        payload TEXT NOT NULL,
        hash TEXT NOT NULL CHECK(typeof(hash)='text' AND length(hash)=71 AND length(CAST(hash AS BLOB))=71 AND substr(hash,1,7)='sha256:' AND substr(hash,8) NOT GLOB '*[^0-9a-f]*'),
        changed_seq INTEGER NOT NULL CHECK(typeof(changed_seq)='integer' AND changed_seq>=1),
        PRIMARY KEY(binding_id),
        FOREIGN KEY(project_id,run_kind,run_id) REFERENCES work_entities(project_id,kind,entity_id),
        FOREIGN KEY(project_id,assignment_kind,assignment_id) REFERENCES work_entities(project_id,kind,entity_id),
        FOREIGN KEY(project_id) REFERENCES work_state(project_id)
    ) WITHOUT ROWID""",
    """CREATE TABLE work_health(
        project_id TEXT NOT NULL,
        issue_id TEXT NOT NULL,
        entity_kind TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        code TEXT NOT NULL,
        severity TEXT NOT NULL CHECK(severity IN('blocking','diagnostic')),
        source_hash TEXT NOT NULL CHECK(typeof(source_hash)='text' AND length(source_hash)=71 AND length(CAST(source_hash AS BLOB))=71 AND substr(source_hash,1,7)='sha256:' AND substr(source_hash,8) NOT GLOB '*[^0-9a-f]*'),
        state TEXT NOT NULL CHECK(state IN('open','resolved')),
        changed_seq INTEGER NOT NULL CHECK(typeof(changed_seq)='integer' AND changed_seq>=1),
        PRIMARY KEY(issue_id),
        FOREIGN KEY(project_id) REFERENCES work_state(project_id)
    ) WITHOUT ROWID""",
    """CREATE TABLE work_scope_reservations(
        project_id TEXT NOT NULL,
        reservation_id TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        entity_kind TEXT NOT NULL DEFAULT 'assignment' CHECK(entity_kind='assignment'),
        revision INTEGER NOT NULL CHECK(typeof(revision)='integer' AND revision>=1),
        generation INTEGER NOT NULL CHECK(typeof(generation)='integer' AND generation>=0),
        scope_version INTEGER NOT NULL CHECK(typeof(scope_version)='integer' AND scope_version>=1),
        scope TEXT NOT NULL,
        active INTEGER NOT NULL CHECK(typeof(active)='integer' AND active IN(0,1)),
        changed_seq INTEGER NOT NULL CHECK(typeof(changed_seq)='integer' AND changed_seq>=1),
        PRIMARY KEY(reservation_id),
        FOREIGN KEY(project_id,entity_kind,entity_id) REFERENCES work_entities(project_id,kind,entity_id),
        FOREIGN KEY(project_id) REFERENCES work_state(project_id)
    ) WITHOUT ROWID""",
    """CREATE INDEX work_entity_status ON work_entities(project_id,kind,status_raw,entity_id) WHERE deleted=0""",
    """CREATE INDEX work_member_lookup ON work_members(project_id,assignment_ref,run_id,ordinal)""",
    """CREATE INDEX work_member_pair ON work_members(project_id,run_id,assignment_ref,ordinal)""",
    """CREATE INDEX work_history_entity ON work_history(project_id,entity_kind,entity_id,seq)""",
    """CREATE INDEX work_history_tail ON work_history(project_id,seq)""",
    """CREATE UNIQUE INDEX work_client_key ON work_operations(project_id,operation_kind,client_key) WHERE client_key IS NOT NULL""",
    """CREATE INDEX work_pending_operations ON work_operation_state(project_id,next_due_at,operation_id) WHERE state IN ('pending','blocked')""",
    """CREATE INDEX work_event_tail ON work_events(project_id,change_seq,event_id)""",
    """CREATE INDEX work_pending_delivery ON work_outbox(project_id,next_due_at,step_id) WHERE status IN ('pending','claimed','blocked')""",
    """CREATE INDEX work_target_delivery ON work_outbox(project_id,target_kind,target_key,target_revision,step_id)""",
    """CREATE INDEX work_health_status ON work_health(project_id,severity,state,issue_id)""",
    """CREATE INDEX work_health_blocking ON work_health(project_id,code,issue_id) WHERE state='open' AND severity='blocking'""",
    """CREATE INDEX work_reservation_active ON work_scope_reservations(project_id,active,reservation_id)""",
)


_MIGRATION_STATEMENTS = (
    """CREATE TABLE work_migrations(
        project_id TEXT NOT NULL,
        migration_id TEXT NOT NULL,
        descriptor_version INTEGER NOT NULL CHECK(typeof(descriptor_version)='integer' AND descriptor_version>=1),
        descriptor_hash TEXT NOT NULL CHECK(typeof(descriptor_hash)='text' AND length(descriptor_hash)=71 AND length(CAST(descriptor_hash AS BLOB))=71 AND substr(descriptor_hash,1,7)='sha256:' AND substr(descriptor_hash,8) NOT GLOB '*[^0-9a-f]*'),
        source_manifest_hash TEXT NOT NULL CHECK(typeof(source_manifest_hash)='text' AND length(source_manifest_hash)=71 AND length(CAST(source_manifest_hash AS BLOB))=71 AND substr(source_manifest_hash,1,7)='sha256:' AND substr(source_manifest_hash,8) NOT GLOB '*[^0-9a-f]*'),
        source_generation INTEGER NOT NULL CHECK(typeof(source_generation)='integer' AND source_generation>=0),
        target_namespace_version INTEGER NOT NULL CHECK(typeof(target_namespace_version)='integer' AND target_namespace_version>=1),
        phase TEXT NOT NULL CHECK(phase IN('planned','importing','verified','ready','blocked')),
        cursor TEXT NOT NULL,
        imported_units INTEGER NOT NULL CHECK(typeof(imported_units)='integer' AND imported_units>=0),
        high_water TEXT NOT NULL,
        verification_hash TEXT CHECK(verification_hash IS NULL OR (typeof(verification_hash)='text' AND length(verification_hash)=71 AND length(CAST(verification_hash AS BLOB))=71 AND substr(verification_hash,1,7)='sha256:' AND substr(verification_hash,8) NOT GLOB '*[^0-9a-f]*')),
        revision INTEGER NOT NULL CHECK(typeof(revision)='integer' AND revision>=1),
        last_error_code TEXT NOT NULL,
        PRIMARY KEY(migration_id),
        UNIQUE(project_id,migration_id),
        FOREIGN KEY(project_id) REFERENCES work_state(project_id)
    ) WITHOUT ROWID""",
)


def _definition(namespace: str, statements: tuple[str, ...]) -> SchemaDefinition:
    raw = json.dumps(
        {"namespace": namespace, "version": 1, "statements": statements},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return SchemaDefinition(
        namespace, 1, statements, "sha256:" + hashlib.sha256(raw).hexdigest()
    )


def work_schema() -> SchemaDefinition:
    """Return work@1 without connecting, inspecting or changing any store."""
    return _definition("work", _WORK_STATEMENTS)


def work_migration_schema() -> SchemaDefinition:
    """Return explicit-maintenance metadata DDL, without running migration."""
    return _definition("work_migration", _MIGRATION_STATEMENTS)
