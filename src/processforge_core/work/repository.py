"""Atomic internal metadata repository over the existing Database/SqlSession.

Cold construction never initializes/imports/activates. Trusted domain planners
and host authorization remain outside this disconnected storage kernel. The
supported variants edit metadata, ordered members and immutable associations;
bindings, reservations, health and pending-completion proofs remain gated.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Literal, cast

from ..database import Database, DatabaseError, SqlSession
from .compact_codec import decode_canonical
from .compact_model import ObjectRef
from .mutation_codec import (
    association_history,
    digest,
    document,
    encode,
    link_payload,
    raw_text,
    use_descriptor,
)
from .mutation_model import (
    AcceptedReceipt,
    AssociationMetadata,
    DeliveryState,
    Encoded,
    EntityFileUse,
    EntityKey,
    HistoryPage,
    HistoryRecord,
    MutationError,
    MutationPlan,
    MutationResult,
    PreparedObject,
    StoreBinding,
    integer,
    text,
)
from .schema import work_schema
from .selection_contract import normalize_objective
from .selection_schema import selection_schema
from .selection_update import (
    Row,
    SelectionUpdater,
    body,
    entity,
    insert,
    number,
    one,
    rows,
    string,
    write,
)

_SCHEMAS = (work_schema(), selection_schema())


class SqlWorkRepository:
    """One transaction coordinator; no new connection wrapper or public writer."""

    def __init__(self, database: Database, binding: StoreBinding) -> None:
        if type(binding) is not StoreBinding:
            raise MutationError("mutation_input_invalid")
        identity = database.target.identity
        if (identity.store_id, identity.scope, identity.owner_id) != (
            binding.store_id,
            "project",
            binding.owner_id,
        ) or not binding.project_id:
            raise MutationError("mutation_store_mismatch")
        self._database, self._binding = database, binding

    def _schema(self, sql: SqlSession) -> None:
        for schema in _SCHEMAS:
            actual = one(
                sql,
                "SELECT version,checksum FROM pf_schema_versions WHERE namespace=?",
                (schema.namespace,),
            )
            if actual is None or (actual["version"], actual["checksum"]) != (
                schema.version,
                schema.checksum,
            ):
                raise MutationError("mutation_schema_unsupported")

    def _state(self, sql: SqlSession) -> Row:
        self._schema(sql)
        p = self._binding.project_id
        state = one(sql, "SELECT * FROM work_state WHERE singleton=1", ())
        selection = one(sql, "SELECT * FROM work_selection_state WHERE p=?", (p,))
        if (
            state is None
            or state["project_id"] != p
            or state["generation"] != self._binding.generation
            or state["authority"] != "sql"
            or state["readiness"] != "ready"
            or state["active_coverage"] != "complete"
            or state["protocol_version"] != 1
            or state["required_features"] != "[]"
            or selection is None
            or selection["coverage_complete"] != 1
            or selection["catalog_revision"] != state["catalog_revision"]
        ):
            raise MutationError("mutation_state_not_ready")
        number(state, "generation")
        number(state, "catalog_revision", 1)
        number(state, "next_change_seq", 1)
        return state

    def _result(self, sql: SqlSession, operation: Row) -> MutationResult:
        state = one(
            sql,
            "SELECT * FROM work_operation_state WHERE project_id=? AND operation_id=?",
            (self._binding.project_id, operation["operation_id"]),
        )
        if state is None:
            raise MutationError("mutation_operation_corrupt")
        # Verify every stored immutable envelope, even if only receipt is returned.
        for version, content, hashed in (
            ("request_version", "request_body", "request_hash"),
            ("accepted_version", "accepted_body", "accepted_hash"),
            ("receipt_version", "receipt", "receipt_hash"),
        ):
            encoded = Encoded(
                string(operation, content).encode("utf-8"),
                number(operation, version, 1),
            )
            if digest(encoded) != operation[hashed]:
                raise MutationError("mutation_operation_corrupt")
        delivery = DeliveryState(
            number(state, "revision", 1),
            cast(Literal["pending", "applied", "blocked"], state["state"]),
            number(state, "pending_steps"),
            string(state, "next_due_at"),
            string(state, "last_error_code"),
        )
        if (delivery.state == "applied") != (delivery.pending_steps == 0):
            raise MutationError("mutation_operation_corrupt")
        return MutationResult(
            "replayed",
            AcceptedReceipt(
                string(operation, "operation_id"),
                number(operation, "accepted_seq", 1),
                Encoded(
                    string(operation, "receipt").encode("utf-8"),
                    number(operation, "receipt_version", 1),
                ),
            ),
            delivery,
        )

    def _request(
        self, sql: SqlSession, kind: str, key: str | None, request: Encoded
    ) -> MutationResult | None:
        if key is None:
            return None
        operation = one(
            sql,
            "SELECT * FROM work_operations WHERE project_id=? AND operation_kind=? AND client_key=?",
            (self._binding.project_id, kind, key),
        )
        if operation is None:
            return None
        # Hash equality is insufficient; compare exact version AND UTF-8 bytes.
        if (
            operation["request_version"] != request.version
            or operation["request_hash"] != digest(request)
            or string(operation, "request_body").encode("utf-8") != request.body
        ):
            raise MutationError("mutation_key_conflict")
        return self._result(sql, operation)

    def lookup_request(
        self, kind: str, key: str | None, request: Encoded
    ) -> MutationResult | None:
        """Exact replay lookup, before today's defaults or stale planning proofs."""
        text(kind, required=True)
        if key is not None:
            text(key)
        if kind != "metadata" or type(request) is not Encoded:
            raise MutationError("mutation_input_invalid")
        with self._database.read() as sql:
            self._state(sql)
            return self._request(sql, kind, key, request)

    def lookup_operation(self, operation_id: str) -> MutationResult | None:
        """Exact operation recovery; never rerun domain selection."""
        text(operation_id, required=True)
        with self._database.read() as sql:
            self._state(sql)
            operation = one(
                sql,
                "SELECT * FROM work_operations WHERE project_id=? AND operation_id=?",
                (self._binding.project_id, operation_id),
            )
            return None if operation is None else self._result(sql, operation)

    def apply(self, plan: MutationPlan) -> MutationResult:
        """Accept only after commit; database ambiguity preserves recovery ID."""
        if type(plan) is not MutationPlan:
            raise MutationError("mutation_capability_unsupported")
        try:
            with self._database.transaction() as sql:
                result = self._apply(sql, plan)
            return result
        except DatabaseError:
            # DatabaseError has no commit/rollback certainty field. Conservatively
            # recover exact identity for all driver/cleanup failures, never retry.
            try:
                with self._database.read() as sql:
                    self._state(sql)
                    recovered = self._replay(sql, plan)
                if recovered is not None:
                    return recovered
            except (DatabaseError, MutationError):
                pass
            raise MutationError("mutation_outcome_unknown", plan.operation_id) from None

    def _replay(self, sql: SqlSession, plan: MutationPlan) -> MutationResult | None:
        keyed = self._request(sql, plan.operation_kind, plan.client_key, plan.request)
        if keyed is not None:
            return keyed
        operation = one(
            sql,
            "SELECT * FROM work_operations WHERE project_id=? AND operation_id=?",
            (self._binding.project_id, plan.operation_id),
        )
        if operation is None:
            return None
        if (
            operation["operation_kind"] != plan.operation_kind
            or operation["client_key"] != plan.client_key
            or operation["request_version"] != plan.request.version
            or operation["request_hash"] != digest(plan.request)
            or string(operation, "request_body").encode("utf-8") != plan.request.body
        ):
            raise MutationError("mutation_operation_conflict")
        return self._result(sql, operation)

    def _apply(self, sql: SqlSession, plan: MutationPlan) -> MutationResult:
        # Bind every replay to the actual current store before reading receipts.
        # This gate checks storage readiness, never the stale entity/read proof.
        state = self._state(sql)
        replay = self._replay(sql, plan)
        if replay is not None:
            return replay
        p, generation = self._binding.project_id, self._binding.generation
        if plan.proof.catalog_revision != state["catalog_revision"]:
            raise MutationError("mutation_catalog_conflict")
        # This slice has no supported invariant path for these capabilities.
        # Refuse even preexisting records rather than leave their semantics stale.
        for table, column in (
            ("work_bindings", "project_id"),
            ("work_scope_reservations", "project_id"),
            ("work_health", "project_id"),
            ("work_valid_pending_edges", "p"),
        ):
            if (
                one(
                    sql,
                    f"SELECT 1 AS present FROM {table} WHERE {column}=? LIMIT 1",
                    (p,),
                )
                is not None
            ):
                raise MutationError("mutation_capability_unsupported")
        before: dict[EntityKey, Row | None] = {}
        expected = {e.key: e.revision for e in plan.proof.entities}
        for proof in plan.proof.entities:
            current = entity(sql, p, proof.key)
            if (
                (current is None) != (proof.revision is None)
                or current is not None
                and (
                    current["revision"] != proof.revision
                    or current["generation"] != generation
                )
            ):
                raise MutationError("mutation_revision_conflict")
            body(current)
            before[proof.key] = current
        for edit in plan.entities:
            document(edit.after.payload)
        objects = {o.object_id: o for o in plan.objects}
        for obj in plan.objects:
            if obj.binding != self._binding:
                raise MutationError("mutation_store_mismatch")
        for use in plan.uses:
            use_obj = objects.get(use.object_id)
            if (
                use.binding != self._binding
                or use_obj is None
                or use.key not in {e.after.key for e in plan.entities}
                or use.revision != (expected.get(use.key) or 0) + 1
            ):
                raise MutationError("mutation_association_invalid")
        if set(objects) != {u.object_id for u in plan.uses}:
            raise MutationError("mutation_association_invalid")
        links = []
        for link_draft in plan.immutable_links:
            if link_draft.use not in plan.uses:
                raise MutationError("mutation_delivery_mismatch")
            payload = link_payload(
                link_draft, objects[link_draft.use.object_id], plan.operation_id
            )
            links.append((link_draft, payload))
        selection = SelectionUpdater(sql, p, plan)
        base = number(state, "next_change_seq", 1)
        end = integer(base + 1 + len(plan.entities) + len(plan.events), 1)
        catalog = integer(number(state, "catalog_revision", 1) + 1, 1)
        # Claim singleton allocation/CAS in the same transaction; no MAX scan.
        write(
            sql,
            "UPDATE work_state SET next_change_seq=?,catalog_revision=? WHERE singleton=1 AND project_id=? AND generation=? AND catalog_revision=? AND next_change_seq=? AND authority='sql' AND readiness='ready' AND active_coverage='complete'",
            (end, catalog, p, generation, state["catalog_revision"], base),
        )
        insert(
            sql,
            "work_operations",
            dict(
                project_id=p,
                operation_id=plan.operation_id,
                operation_kind=plan.operation_kind,
                client_key=plan.client_key,
                request_version=plan.request.version,
                request_hash=digest(plan.request),
                request_body=plan.request.body.decode("utf-8"),
                accepted_version=plan.accepted.version,
                accepted_hash=digest(plan.accepted),
                accepted_body=plan.accepted.body.decode("utf-8"),
                receipt_version=plan.receipt.version,
                receipt=plan.receipt.body.decode("utf-8"),
                receipt_hash=digest(plan.receipt),
                accepted_seq=base,
                origin=plan.origin,
            ),
        )
        for obj in plan.objects:
            self._object(sql, obj)
        for i, edit in enumerate(plan.entities):
            after = edit.after
            old_revision = expected[after.key]
            revision = integer((old_revision or 0) + 1, 1)
            data = document(after.payload)
            objective = raw_text(data.get("objective"))
            session = data.get("session")
            values: Row = dict(
                revision=revision,
                generation=generation,
                payload_version=after.payload.version,
                payload=after.payload.body.decode("utf-8"),
                payload_hash=digest(after.payload),
                changed_seq=base + 1 + i,
                source_order=after.source_order,
                integrity=after.integrity,
                source_ref=None,
                status_raw=raw_text(data.get("status")),
                objective_raw=objective,
                objective_normalized=normalize_objective(objective),
                created_lex=raw_text(data.get("created_at")),
                updated_lex=raw_text(data.get("updated_at")),
                process_ref=raw_text(data.get("process")),
                context_ref=raw_text(data.get("context_id")),
                session_id=raw_text(session.get("id"))
                if isinstance(session, Mapping)
                else "",
                deleted=0,
            )
            if old_revision is None:
                insert(
                    sql,
                    "work_entities",
                    dict(
                        project_id=p,
                        kind=after.key.kind,
                        entity_id=after.key.entity_id,
                        **values,
                    ),
                )
            else:
                write(
                    sql,
                    "UPDATE work_entities SET "
                    + ",".join(k + "=?" for k in values)
                    + " WHERE project_id=? AND kind=? AND entity_id=? AND revision=? AND generation=?",
                    (
                        *values.values(),
                        p,
                        after.key.kind,
                        after.key.entity_id,
                        old_revision,
                        generation,
                    ),
                )
            history = association_history(
                edit.history, tuple(u for u in plan.uses if u.key == after.key)
            )
            insert(
                sql,
                "work_history",
                dict(
                    project_id=p,
                    seq=base + 1 + i,
                    operation_id=plan.operation_id,
                    entity_kind=after.key.kind,
                    entity_id=after.key.entity_id,
                    entity_revision=revision,
                    record_version=history.version,
                    history_kind=edit.history_kind,
                    body=history.body.decode("utf-8"),
                    body_hash=digest(history),
                    occurred_at=edit.occurred_at,
                ),
            )
            if (
                after.key.kind == "assignment"
                and after.key.entity_id == "first-assignment"
            ):
                standalone = one(
                    sql,
                    "SELECT * FROM work_standalone_selection WHERE p=? AND a='first-assignment'",
                    (p,),
                )
                if (standalone is None) != (old_revision is None):
                    raise MutationError("selection_invariant_failed")
                prior = before[after.key]
                if (
                    standalone is not None
                    and prior is not None
                    and (
                        standalone["revision"] != old_revision
                        or standalone["objective_raw"] != prior["objective_raw"]
                        or standalone["status_raw"] != prior["status_raw"]
                        or standalone["process_raw"] != prior["process_ref"]
                    )
                ):
                    raise MutationError("selection_invariant_failed")
                if standalone is None:
                    insert(
                        sql,
                        "work_standalone_selection",
                        dict(
                            p=p,
                            a="first-assignment",
                            objective_raw=objective,
                            status_raw=values["status_raw"],
                            process_raw=values["process_ref"],
                            revision=revision,
                        ),
                    )
                else:
                    write(
                        sql,
                        "UPDATE work_standalone_selection SET objective_raw=?,status_raw=?,process_raw=?,revision=? WHERE p=? AND a='first-assignment' AND revision=?",
                        (
                            objective,
                            values["status_raw"],
                            values["process_ref"],
                            revision,
                            p,
                            old_revision,
                        ),
                    )
        for use in plan.uses:
            insert(
                sql,
                "work_entity_files",
                dict(
                    project_id=p,
                    entity_kind=use.key.kind,
                    entity_id=use.key.entity_id,
                    entity_revision=use.revision,
                    object_id=use.object_id,
                    role=use.role,
                    ordinal=use.ordinal,
                ),
            )
        for change in plan.members:
            old = one(
                sql,
                "SELECT ordinal FROM work_members WHERE project_id=? AND run_id=? AND ordinal=?",
                (p, change.run_id, change.ordinal),
            )
            if change.after is None:
                if old is None:
                    raise MutationError("mutation_member_missing")
                write(
                    sql,
                    "DELETE FROM work_members WHERE project_id=? AND run_id=? AND ordinal=?",
                    (p, change.run_id, change.ordinal),
                )
            else:
                decoded = decode_canonical(change.after.body)
                ref = (
                    raw_text(decoded.get("id")) if isinstance(decoded, Mapping) else ""
                )
                status = (
                    raw_text(decoded.get("status"))
                    if isinstance(decoded, Mapping)
                    else ""
                )
                if old is None:
                    insert(
                        sql,
                        "work_members",
                        dict(
                            project_id=p,
                            run_id=change.run_id,
                            ordinal=change.ordinal,
                            assignment_ref=ref,
                            member_status=status,
                            member_payload=change.after.body.decode("utf-8"),
                        ),
                    )
                else:
                    write(
                        sql,
                        "UPDATE work_members SET assignment_ref=?,member_status=?,member_payload=? WHERE project_id=? AND run_id=? AND ordinal=?",
                        (
                            ref,
                            status,
                            change.after.body.decode("utf-8"),
                            p,
                            change.run_id,
                            change.ordinal,
                        ),
                    )
        selection.apply()
        for i, event in enumerate(plan.events):
            insert(
                sql,
                "work_events",
                dict(
                    project_id=p,
                    event_id=event.event_id,
                    operation_id=plan.operation_id,
                    ordinal=event.ordinal,
                    event_type=event.event_type,
                    event_version=event.envelope.version,
                    canonical_envelope=event.envelope.body.decode("utf-8"),
                    envelope_hash=digest(event.envelope),
                    change_seq=base + 1 + len(plan.entities) + i,
                ),
            )
        deliveries = list(plan.deliveries)
        for link, payload in links:
            # Keep the legacy inert draft variant closed; association drafts have
            # a separate typed boundary and are persisted only here.
            insert(
                sql,
                "work_outbox",
                dict(
                    project_id=p,
                    step_id=link.step_id,
                    operation_id=plan.operation_id,
                    ordinal=link.ordinal,
                    target_kind="immutable_link",
                    target_key=link.target_key,
                    target_revision=link.use.revision,
                    payload_version=payload.version,
                    payload=payload.body.decode("utf-8"),
                    payload_hash=digest(payload),
                    status="pending",
                    next_due_at=link.due_at,
                    claim_epoch=0,
                    attempt_count=0,
                    last_error_code="",
                ),
            )
        for draft in deliveries:
            insert(
                sql,
                "work_outbox",
                dict(
                    project_id=p,
                    step_id=draft.step_id,
                    operation_id=plan.operation_id,
                    ordinal=draft.ordinal,
                    target_kind=draft.target_kind,
                    target_key=draft.target_key,
                    target_revision=draft.target_revision,
                    payload_version=draft.payload.version,
                    payload=draft.payload.body.decode("utf-8"),
                    payload_hash=digest(draft.payload),
                    status="pending",
                    next_due_at=draft.due_at,
                    claim_epoch=0,
                    attempt_count=0,
                    last_error_code="",
                ),
            )
        due = min(
            [d.due_at for d in plan.deliveries]
            + [d.due_at for d in plan.immutable_links],
            default="",
        )
        pending = len(plan.deliveries) + len(plan.immutable_links)
        insert(
            sql,
            "work_operation_state",
            dict(
                project_id=p,
                operation_id=plan.operation_id,
                revision=1,
                state="pending" if pending else "applied",
                next_due_at=due,
                last_error_code="",
                pending_steps=pending,
            ),
        )
        write(
            sql,
            "UPDATE work_selection_state SET catalog_revision=? WHERE p=? AND catalog_revision=? AND coverage_complete=1",
            (catalog, p, state["catalog_revision"]),
        )
        operation = one(
            sql,
            "SELECT * FROM work_operations WHERE project_id=? AND operation_id=?",
            (p, plan.operation_id),
        )
        assert operation is not None
        return replace(self._result(sql, operation), acceptance="accepted")

    def _object(self, sql: SqlSession, obj: PreparedObject) -> None:
        values: Row = dict(
            project_id=self._binding.project_id,
            object_id=obj.object_id,
            hash="sha256:" + obj.ref.digest,
            size=obj.ref.size,
            media_type="application/octet-stream",
            ref_version=1,
            relative_path=obj.relative_path,
            role="object",
            immutable=1,
        )
        existing = one(
            sql, "SELECT * FROM work_file_refs WHERE object_id=?", (obj.object_id,)
        )
        locator = one(
            sql,
            "SELECT * FROM work_file_refs WHERE project_id=? AND relative_path=?",
            (self._binding.project_id, obj.relative_path),
        )
        if existing is not None or locator is not None:
            if existing != values or locator != values:
                raise MutationError("mutation_object_conflict")
        else:
            insert(sql, "work_file_refs", values)

    def lookup_association(
        self,
        key: EntityKey,
        revision: int,
        role: str,
        ordinal: int,
    ) -> AssociationMetadata | None:
        """Exact metadata lookup; caller authorizes access, body I/O is separate."""
        if type(key) is not EntityKey:
            raise MutationError("mutation_input_invalid")
        integer(revision, 1)
        integer(ordinal)
        text(role, required=True)
        with self._database.read() as sql:
            self._state(sql)
            row = one(
                sql,
                "SELECT f.*,h.body AS history_body,h.body_hash AS history_hash,h.record_version "
                "FROM work_entity_files u JOIN work_file_refs f ON f.project_id=u.project_id AND f.object_id=u.object_id "
                "JOIN work_history h ON h.project_id=u.project_id AND h.entity_kind=u.entity_kind AND h.entity_id=u.entity_id AND h.entity_revision=u.entity_revision "
                "WHERE u.project_id=? AND u.entity_kind=? AND u.entity_id=? AND u.entity_revision=? AND u.role=? AND u.ordinal=?",
                (
                    self._binding.project_id,
                    key.kind,
                    key.entity_id,
                    revision,
                    role,
                    ordinal,
                ),
            )
            if row is None:
                return None
            history = Encoded(
                string(row, "history_body").encode("utf-8"),
                number(row, "record_version", 1),
            )
            if digest(history) != row["history_hash"]:
                raise MutationError("mutation_history_corrupt")
            doc = decode_canonical(history.body)
            if (
                not isinstance(doc, Mapping)
                or set(doc) != {"version", "kind", "metadata", "uses"}
                or type(doc["version"]) is not int
                or doc["version"] != 1
                or doc["kind"] != "object_associations"
                or not isinstance(doc["uses"], tuple)
            ):
                raise MutationError("mutation_history_corrupt")
            matches = [
                u
                for u in doc["uses"]
                if isinstance(u, Mapping)
                and u.get("role") == role
                and u.get("ordinal") == ordinal
            ]
            if len(matches) != 1:
                raise MutationError("mutation_history_corrupt")
            desc = matches[0]
            assert isinstance(desc, Mapping)
            use = EntityFileUse(
                self._binding,
                key,
                revision,
                string(row, "object_id"),
                role,
                ordinal,
                text(desc.get("codec"), required=True),
                text(desc.get("media_type"), required=True),
                text(desc.get("logical_reference")),
                text(desc.get("evidence_status")),
            )
            if encode(desc) != use_descriptor(use):
                raise MutationError("mutation_history_corrupt")
            ref = ObjectRef(
                "sha256",
                string(row, "hash").removeprefix("sha256:"),
                number(row, "size"),
                use.media_type,
                use.codec,
            )
            from .compact_objects import object_relative_path

            path = object_relative_path(ref).as_posix()
            if (
                row["media_type"],
                row["role"],
                row["ref_version"],
                row["immutable"],
                row["relative_path"],
            ) != ("application/octet-stream", "object", 1, 1, path):
                raise MutationError("mutation_object_conflict")
            if string(row, "object_id") != digest(
                encode((self._binding.project_id, path))
            ):
                raise MutationError("mutation_object_conflict")
            return AssociationMetadata(use, ref, path)

    def history(
        self, key: EntityKey, *, after_seq: int = 0, limit: int = 100
    ) -> HistoryPage:
        """Explicit keyset read; ordinary mutation never materializes history."""
        if type(key) is not EntityKey:
            raise MutationError("mutation_input_invalid")
        integer(after_seq)
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise MutationError("mutation_input_invalid")
        with self._database.read() as sql:
            self._state(sql)
            found = rows(
                sql,
                "SELECT * FROM work_history WHERE project_id=? AND entity_kind=? AND entity_id=? AND seq>? ORDER BY seq LIMIT ?",
                (
                    self._binding.project_id,
                    key.kind,
                    key.entity_id,
                    after_seq,
                    limit + 1,
                ),
            )
            records = []
            for row in found[:limit]:
                encoded = Encoded(
                    string(row, "body").encode("utf-8"),
                    number(row, "record_version", 1),
                )
                if digest(encoded) != row["body_hash"]:
                    raise MutationError("mutation_history_corrupt")
                records.append(
                    HistoryRecord(
                        number(row, "seq", 1),
                        string(row, "operation_id"),
                        key,
                        number(row, "entity_revision", 1),
                        encoded,
                        string(row, "history_kind"),
                        string(row, "occurred_at"),
                    )
                )
            return HistoryPage(
                tuple(records), records[-1].seq if len(found) > limit else None
            )
