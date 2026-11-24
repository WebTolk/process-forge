"""Online adoption of one enrolled project's existing SQLite event journal."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import time
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Literal
from uuid import uuid4

from ..configuration import ConfigurationProvider
from ..database import DatabaseFactory, SQLiteDriver
from ..database.errors import DatabaseError
from ..executions.composition import _execution_profile
from ..executions.model import ExecutionError
from ..executions.projection import canonical_json
from ..project.metadata import ProjectMetadataReader, declared_workplace_id
from ..runtime.execution_admission import (
    ExecutionAdmission,
    PreparedRegistryOwner,
    RegistryLockTimeout,
    prepare_registry_owner,
    try_registry_file_lock,
    wait_registry_file_lock,
)
from .backup import SQLiteBackupService
from .contracts import (
    JsonObject,
    MaintenanceError,
    StorageMigrationContext,
    StoreTarget,
)
from .execution_migration import _atomic, _hash, _read, _read_code_document
from .journal_scan import execution_bytes, execution_json
from .project_event_maintenance import (
    PROJECT_EVENT_MAINTENANCE_BUSY,
    _intent,
    project_event_operation_intent,
    require_compatible_runtime,
    require_imported_history,
)
from .project_event_owner import (
    ProjectEventBinding,
    project_event_binding_path,
    read_project_event_binding,
    require_project_event_binding,
)
from .project_event_publication import (
    PublicationConflict,
    _sync_parent,
    publish_immutable_bytes,
)
from .storage_migration import (
    MIGRATION_ID as V1_MIGRATION_ID,
)
from .storage_migration import (
    StorageMigrationService,
    _admission_held,
    _checksum,
    _connection,
    _deadline,
    _descriptor,
    _inspect_target,
    _legacy_facts,
    _pins,
    _publish_pin,
    _safe,
    _TargetScan,
    _uuid,
    add_store_identity,
    storage_identity_gate,
    storage_owner_root,
    validate_storage_context,
)

MIGRATION_ID = "r02-project-events-v2"
_V1_DESCRIPTOR = (
    "sha256:a56d3dc302dd9556d72bc93390c65590233d69fcee8e303c2a8461fa8286cdfc"
)
_TRANSFORM_PATHS = (
    "src/processforge_core/maintenance/project_event_coordinator.py",
    "src/processforge_core/maintenance/project_event_maintenance.py",
    "src/processforge_core/maintenance/project_event_owner.py",
    "src/processforge_core/maintenance/project_event_publication.py",
    "src/processforge_core/runtime/execution_admission.py",
    "src/processforge_core/runtime/process_identity.py",
    "src/processforge_core/runtime_service_state.py",
    "src/processforge_platforms/linux_process_identity.py",
)
_TARGET_KEYS = ("kind", "scope", "owner_id", "target_relative_path")
_PLAN_KEYS = {
    *_TARGET_KEYS,
    "schema_version",
    "migration_id",
    "mode",
    "descriptor_checksum",
    "store_id",
    "source_generation",
    "target_generation",
    "safety_generation",
    "source",
    "plan_checksum",
}
_EVIDENCE_CONFLICT = "storage_project_event_evidence_conflict"
_PLAN_MISSING = "storage_project_event_plan_missing"
_TARGET_UNKNOWN = "storage_project_event_target_owner_unknown"
_BINDING_UNKNOWN = "storage_project_event_binding_owner_unknown"
_EVENT_PATH = "runtime/events/events.sqlite3"
_PENDING_STATES = ("planned", "backed_up", "importing", "verified")
_READY_STATES = ("verified", "ready")


def _online_descriptor() -> JsonObject:
    root = Path(__file__).absolute().parents[3]
    path = root / "schemas/project-event-migration-v2.json"
    try:
        descriptor = _read_code_document(path)
        files = [
            {
                "relative_path": path,
                "sha256": "sha256:"
                + hashlib.sha256((root / path).read_bytes()).hexdigest(),
            }
            for path in _TRANSFORM_PATHS
        ]
    except (OSError, ValueError) as error:
        raise MaintenanceError("storage_transform_changed") from error
    expected = {
        "migration_id": MIGRATION_ID,
        "descriptor_version": 2,
        "min_reader_capability": "storage-identity-v1",
        "min_writer_capability": "storage-identity-v1",
        "legacy_descriptor_checksum": _V1_DESCRIPTOR,
        "transform_files": files,
        "transform_checksum": _hash(files),
    }
    if canonical_json(descriptor) != canonical_json(expected):
        raise MaintenanceError("storage_transform_changed")
    return descriptor


def _target_facts(target: StoreTarget) -> JsonObject:
    return {key: getattr(target, key) for key in _TARGET_KEYS}


def _full_context(
    context: StorageMigrationContext, root: Path, main: str
) -> StorageMigrationContext:
    """Rebuild the released producer's insertion order before narrowing."""
    (events,) = context.targets
    workplace = context.workplace_root
    assert workplace is not None
    raw = "runtime/agent-events/hooks.sqlite3"
    targets = [
        events,
        StoreTarget("raw", root / raw, raw, "project", events.owner_id),
        StoreTarget("main", root / main, main, "project", events.owner_id),
    ]
    routes: tuple[tuple[Literal["raw", "search", "accounting"], str, str | None], ...]
    workplace_id = declared_workplace_id(_safe(workplace / "workplace.yaml"))
    origin = _safe(workplace / "data/accounting/identity.json")
    origin_id = None
    if origin.exists():
        origin_id = _read(origin).get("origin_id")
        if not isinstance(origin_id, str) or not origin_id.strip():
            raise MaintenanceError("owner_identity_required")
    routes = (
        ("raw", "runtime/agent-events/hooks.sqlite3", workplace_id),
        ("search", "runtime/search/local-resource-search.sqlite", workplace_id),
        ("accounting", "data/accounting/accounting.sqlite3", origin_id),
    )
    unqualified = []
    for kind, relative, owner_id in routes:
        if owner_id is None:
            unqualified.append((kind, workplace / relative))
        else:
            targets.append(
                StoreTarget(kind, workplace / relative, relative, "workplace", owner_id)
            )
    result = replace(
        context, targets=tuple(targets), unqualified_targets=tuple(unqualified)
    )
    validate_storage_context(result)
    return result


def _generation(tag: str, context: StorageMigrationContext, config: JsonObject) -> str:
    return _hash(
        {
            "maintenance": tag,
            "project": str(context.project_root),
            "workplace": str(context.workplace_root),
            "device": str(context.device_config_path),
            "configuration": config,
            "targets": [
                (target.kind, str(target.target), target.scope, target.owner_id)
                for target in context.targets
            ],
        }
    )


def _read_optional(path: Path) -> JsonObject | None:
    return _read(path) if _safe(path).exists() else None


def _canonical_bytes(document: JsonObject) -> bytes:
    return (canonical_json(document) + "\n").encode("utf-8")


def _read_plan(path: Path) -> tuple[JsonObject, bytes]:
    try:
        data = execution_bytes(_safe(path))
        plan = execution_json(data)
    except (OSError, ValueError) as error:
        raise MaintenanceError(_EVIDENCE_CONFLICT) from error
    if (
        set(plan) != _PLAN_KEYS
        or data != _canonical_bytes(plan)
        or plan["plan_checksum"]
        != _hash({key: value for key, value in plan.items() if key != "plan_checksum"})
    ):
        raise MaintenanceError(_EVIDENCE_CONFLICT)
    relative = plan["target_relative_path"]
    if not isinstance(relative, str):
        raise MaintenanceError(_EVIDENCE_CONFLICT)
    path_value = PurePosixPath(relative)
    if (
        path_value.is_absolute()
        or path_value.as_posix() != relative
        or not path_value.parts
        or ".." in path_value.parts
        or "\\" in relative
        or ":" in relative
    ):
        raise MaintenanceError(_EVIDENCE_CONFLICT)
    return plan, data


def _children(path: Path) -> Iterator[Path]:
    if _safe(path).exists():
        yield from path.iterdir()


def _matches_target(root: Path, relative: str, target: StoreTarget) -> bool:
    path = root / relative
    if path == target.target:
        return True
    try:
        return _safe(path).samefile(target.target)
    except FileNotFoundError:
        return False


@dataclass(frozen=True)
class _Evidence:
    plan: JsonObject
    data: bytes
    slot: JsonObject | None
    journal: JsonObject | None
    plan_present: bool

    @property
    def checksum(self) -> str:
        return str(self.plan["plan_checksum"])

    @property
    def store_id(self) -> str:
        return str(self.plan["store_id"])

    @property
    def ready(self) -> bool:
        return self.slot is not None and self.slot["state"] == "ready"


def _discover(root: Path, target: StoreTarget, deadline: float) -> _Evidence | None:
    """Find the physical target across owners and both plan versions."""
    namespace = _safe(root / "data/storage-migrations" / V1_MIGRATION_ID)
    selector = StorageMigrationService._selector(root, target)
    slot = None
    try:
        pins = _pins(root)
    except TypeError as error:
        raise MaintenanceError("storage_pin_invalid") from error
    for candidate in pins["slots"]:
        if _matches_target(root, candidate["target_relative_path"], target):
            if slot is not None or _target_facts(target) != {
                key: candidate[key] for key in _TARGET_KEYS
            }:
                raise MaintenanceError("storage_identity_conflict")
            slot = candidate
    selected: tuple[JsonObject, bytes] | None = None
    selectors: set[str] = set()
    for path in _children(selector.parent):
        _deadline(deadline)
        # Private, abandoned publisher staging has no authority.
        if not path.name.lower().endswith(".json"):
            continue
        plan, data = _read_plan(path)
        checksum = plan["plan_checksum"]
        if checksum in selectors:
            raise MaintenanceError(_EVIDENCE_CONFLICT)
        selectors.add(checksum)
        if path == selector or _matches_target(
            root, plan["target_relative_path"], target
        ):
            if selected is not None or path != selector:
                raise MaintenanceError(_EVIDENCE_CONFLICT)
            selected = plan, data

    selected_checksum = selected[0]["plan_checksum"] if selected else None
    plan_present = False
    for path in _children(namespace):
        _deadline(deadline)
        if path == selector.parent:
            continue
        checksum = "sha256:" + path.name
        evidence_path = _safe(path / "plan.json")
        if not _checksum(checksum) and not evidence_path.exists():
            continue
        if not evidence_path.exists():
            if checksum not in selectors or any(
                _safe(path / name).exists()
                for name in ("journal.json", "backup", "report.json")
            ):
                raise MaintenanceError(_EVIDENCE_CONFLICT)
            continue
        plan, raw = _read_plan(evidence_path)
        if checksum == selected_checksum or _matches_target(
            root, plan["target_relative_path"], target
        ):
            if selected is None or checksum != selected_checksum or raw != selected[1]:
                raise MaintenanceError(_EVIDENCE_CONFLICT)
            plan_present = True

    if selected is None:
        if slot is not None:
            raise MaintenanceError(_EVIDENCE_CONFLICT)
        return None
    plan, data = selected
    if _target_facts(target) != {key: plan[key] for key in _TARGET_KEYS}:
        raise MaintenanceError("storage_identity_conflict")
    if slot is not None and (
        not plan_present
        or slot["plan_checksum"] != selected_checksum
        or slot["store_id"] != plan["store_id"]
    ):
        raise MaintenanceError(_EVIDENCE_CONFLICT)
    directory = StorageMigrationService._journal(root, plan["plan_checksum"])
    journal = _read_optional(directory / "journal.json")
    ready = slot is not None and slot["state"] == "ready"
    if not ready and _safe(directory / "report.json").exists():
        raise MaintenanceError(_EVIDENCE_CONFLICT)
    if journal is not None and (
        set(journal)
        != {"state", "store_id", "plan_checksum", "backup_manifest_checksum"}
        or journal["store_id"] != plan["store_id"]
        or journal["plan_checksum"] != selected_checksum
        or journal["state"] not in (*_PENDING_STATES, "ready")
        or (
            journal["backup_manifest_checksum"] is not None
            if journal["state"] == "planned"
            else not _checksum(journal["backup_manifest_checksum"])
        )
    ):
        raise MaintenanceError("storage_journal_conflict")
    if slot is None and (
        (journal is not None and journal["state"] != "planned")
        or _safe(directory / "backup").exists()
    ):
        raise MaintenanceError(_EVIDENCE_CONFLICT)
    if slot is not None:
        allowed = _READY_STATES if ready else _PENDING_STATES
        if (journal is not None and journal["state"] not in allowed) or (
            journal is None and slot["state"] == "pending"
        ):
            raise MaintenanceError("storage_journal_conflict")
    return _Evidence(plan, data, slot, journal, plan_present)


def _authentic_plan(
    plan: JsonObject,
    descriptors: dict[str, str],
    generations: dict[str, tuple[str, ...]],
    released_generation: Callable[[], str],
) -> None:
    migration = plan["migration_id"]
    source = plan["source"]
    _uuid(plan["store_id"])
    if (
        not isinstance(migration, str)
        or migration not in descriptors
        or descriptors[migration] != plan["descriptor_checksum"]
        or type(plan["schema_version"]) is not int
        or plan["schema_version"] != 1
        or plan["mode"] != "existing"
        or type(plan["source_generation"]) is not int
        or plan["source_generation"] != 0
        or type(plan["target_generation"]) is not int
        or plan["target_generation"] != 1
        or not isinstance(source, dict)
        or set(source)
        != {
            "state",
            "application_id",
            "user_version",
            "schema_checksum",
            "store_id",
            "parity",
        }
        or source["state"] != "legacy"
        or source["store_id"] is not None
    ):
        raise MaintenanceError("storage_plan_changed")
    generation = plan["safety_generation"]
    if generation not in generations[migration] and (
        migration != V1_MIGRATION_ID or generation != released_generation()
    ):
        raise MaintenanceError("storage_safety_changed")


def _require_parity(evidence: _Evidence, facts: JsonObject) -> None:
    store_id = facts.get("store_id")
    expected = {**evidence.plan["source"], "store_id": store_id}
    if store_id not in (None, evidence.store_id) or canonical_json(
        facts
    ) != canonical_json(expected):
        raise MaintenanceError("storage_source_changed")


def _new_plan(
    target: StoreTarget, descriptor: str, generation: str, facts: JsonObject
) -> _Evidence:
    plan = {
        **_target_facts(target),
        "schema_version": 1,
        "migration_id": MIGRATION_ID,
        "mode": "existing",
        "descriptor_checksum": descriptor,
        "source_generation": 0,
        "target_generation": 1,
        "safety_generation": generation,
        "source": facts,
        "store_id": uuid4().hex,
    }
    plan["plan_checksum"] = _hash(plan)
    return _Evidence(plan, _canonical_bytes(plan), None, None, False)


def _lock_path(path: Path) -> Path:
    for suffix in (".lock", ".lock.guard"):
        _safe(path.with_name(f".{path.name}{suffix}"))
    return path


@contextmanager
def _wait(path: Path, deadline: float, unknown: str) -> Iterator[None]:
    _deadline(deadline)
    with ExitStack() as gates:
        try:
            gates.enter_context(
                wait_registry_file_lock(
                    _lock_path(path), deadline=deadline, stale_after_seconds=0
                )
            )
        except RegistryLockTimeout as error:
            if error.assessment in {"guard_busy", "owner_live"}:
                code = PROJECT_EVENT_MAINTENANCE_BUSY
            elif error.assessment in {"owner_dead", "deadline_expired"}:
                code = "storage_deadline_exceeded"
            else:
                code = unknown
            raise MaintenanceError(code) from error
        _deadline(deadline)
        yield


@contextmanager
def _publication_guards(
    context: StorageMigrationContext,
    target_gate: Path,
    binding_gate: Path,
    owner: PreparedRegistryOwner,
    deadline: float,
) -> Iterator[None]:
    assert context.project_root is not None
    admission = ExecutionAdmission()
    gates = ((target_gate, _TARGET_UNKNOWN), (binding_gate, _BINDING_UNKNOWN))
    while True:
        _deadline(deadline)
        with ExitStack() as access:
            contested = None
            with admission.start(
                context.project_root, context.workplace_root, deadline=deadline
            ):
                for path, unknown in gates:
                    _deadline(deadline)
                    result = access.enter_context(
                        try_registry_file_lock(_lock_path(path), owner=owner)
                    )
                    if result != "acquired":
                        contested = path, unknown
                        break
            if contested is None:
                _deadline(deadline)
                yield
                return
        # Probe and wait only after both admission leases and the first gate unwind.
        path, unknown = contested
        with _wait(path, deadline, unknown):
            pass


def _durable_parents(path: Path, root: Path, deadline: float) -> None:
    _deadline(deadline)
    _safe(path).mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        # A retry also syncs any parents created by a preceding interrupted process.
        while path != root:
            _sync_parent(path)
            path = path.parent


@dataclass(frozen=True)
class _Coordinator:
    context: StorageMigrationContext
    binding: ProjectEventBinding
    root: Path
    target: StoreTarget
    driver: SQLiteDriver
    legacy: JsonObject
    deadline: float

    def authorize(self) -> None:
        require_project_event_binding(self.binding)
        require_compatible_runtime(self.binding.workplace_manifest.parent)
        _deadline(self.deadline)

    @contextmanager
    def scan(self, *, parity: bool) -> Iterator[_TargetScan]:
        """Keep the SQLite change witness open after releasing the target guard."""
        path = self.target.target
        info = _safe(path).stat()
        with _connection(path, self.driver, deadline=self.deadline) as connection:
            before = connection.execute("PRAGMA data_version").fetchone()[0]
            connection.execute("BEGIN")
            try:
                facts = {
                    "state": "legacy",
                    **_legacy_facts(
                        connection,
                        self.target,
                        self.legacy,
                        parity=parity,
                        deadline=self.deadline,
                    ),
                }
            finally:
                connection.rollback()
            scan = _TargetScan(
                self.target, connection, facts, before, (info.st_dev, info.st_ino)
            )
            scan.revalidate(self.legacy, self.deadline)
            yield scan

    def backup(self) -> SQLiteBackupService:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise MaintenanceError("storage_deadline_exceeded")
        return SQLiteBackupService(driver=self.driver, timeout=min(10.0, remaining))

    def create_backup(self, bundle: Path) -> None:
        _deadline(self.deadline)
        # The target guard excludes other publishers. Keep an interrupted copy
        # in its private staging directory, never at the plan's final name.
        with TemporaryDirectory(prefix=".backup-stage-", dir=bundle.parent) as name:
            staging = Path(name) / bundle.name
            self.backup().create(self.target.target, staging)
            if _safe(bundle).exists():
                raise MaintenanceError("storage_backup_conflict")
            _deadline(self.deadline)
            os.rename(staging, bundle)

    def backup_checksum(self, evidence: _Evidence) -> str:
        bundle = self.directory(evidence) / "backup"
        if not _safe(bundle).exists():
            raise MaintenanceError("storage_backup_missing")
        checked = self.backup().verify(bundle)
        checksum = "sha256:" + str(checked.get("manifest_sha256"))
        if checked.get("verified") is not True or not _checksum(checksum):
            raise MaintenanceError("storage_backup_unverified")
        recorded = evidence.journal and evidence.journal["backup_manifest_checksum"]
        if recorded is not None and recorded != checksum:
            raise MaintenanceError("storage_backup_changed")
        before = _inspect_target(
            replace(self.target, target=bundle / "database.sqlite3"),
            self.legacy,
            self.driver,
            parity=True,
            deadline=self.deadline,
        )
        if canonical_json(before) != canonical_json(evidence.plan["source"]):
            raise MaintenanceError("storage_backup_conflict")
        return checksum

    def discover(self) -> _Evidence | None:
        return _discover(self.root, self.target, self.deadline)

    def directory(self, evidence: _Evidence) -> Path:
        return StorageMigrationService._journal(self.root, evidence.checksum)

    def journal(self, evidence: _Evidence, state: str, checksum: str | None) -> None:
        _deadline(self.deadline)
        _atomic(
            self.directory(evidence) / "journal.json",
            {
                "state": state,
                "store_id": evidence.store_id,
                "plan_checksum": evidence.checksum,
                "backup_manifest_checksum": checksum,
            },
        )

    def pending(self, evidence: _Evidence) -> None:
        selector = StorageMigrationService._selector(self.root, self.target)
        directory = self.directory(evidence)
        _durable_parents(selector.parent, self.root, self.deadline)
        try:
            _deadline(self.deadline)
            publish_immutable_bytes(selector, evidence.data)
            _durable_parents(directory, self.root, self.deadline)
            _deadline(self.deadline)
            publish_immutable_bytes(_safe(directory / "plan.json"), evidence.data)
        except PublicationConflict as error:
            raise MaintenanceError(_EVIDENCE_CONFLICT) from error
        if evidence.journal is None:
            self.journal(evidence, "planned", None)
        _deadline(self.deadline)
        _publish_pin(
            self.root, self.target, evidence.store_id, evidence.checksum, "pending"
        )

    def commit_identity(
        self, evidence: _Evidence, binding_gate: Path, checksum: str
    ) -> None:
        with _wait(binding_gate, self.deadline, _BINDING_UNKNOWN):
            self.authorize()
            require_imported_history(self.target, self.driver)
            self.journal(evidence, "importing", checksum)
            with _connection(
                self.target.target, self.driver, writable=True, deadline=self.deadline
            ) as connection:
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute("BEGIN IMMEDIATE")
                facts = {
                    "state": "legacy",
                    **_legacy_facts(
                        connection,
                        self.target,
                        self.legacy,
                        parity=True,
                        deadline=self.deadline,
                    ),
                }
                if canonical_json(facts) != canonical_json(evidence.plan["source"]):
                    raise MaintenanceError("storage_source_changed")
                _deadline(self.deadline)
                add_store_identity(connection, self.target, evidence.store_id)
                _deadline(self.deadline)
                require_compatible_runtime(self.binding.workplace_manifest.parent)
                require_project_event_binding(self.binding)
                _deadline(self.deadline)
                connection.commit()

    def apply_identity(
        self, evidence: _Evidence, facts: JsonObject, binding_gate: Path
    ) -> str:
        journal = evidence.journal
        assert journal is not None
        state = journal["state"]
        store_id = facts.get("store_id")
        if (state == "verified" and store_id is None) or (
            state in ("planned", "backed_up") and store_id is not None
        ):
            raise MaintenanceError("storage_journal_conflict")
        bundle = self.directory(evidence) / "backup"
        if not _safe(bundle).exists():
            if state != "planned":
                raise MaintenanceError("storage_backup_missing")
            self.create_backup(bundle)
        checksum = self.backup_checksum(evidence)
        if state == "planned":
            self.journal(evidence, "backed_up", checksum)
        if store_id is None:
            self.commit_identity(evidence, binding_gate, checksum)
        return checksum

    def ready(self, evidence: _Evidence, checksum: str) -> None:
        report = self.directory(evidence) / "report.json"
        expected = {
            "schema_version": 1,
            "status": "ready",
            "plan_checksum": evidence.checksum,
            "store_id": evidence.store_id,
            "target_relative_path": self.target.target_relative_path,
        }
        previous = _read_optional(report)
        if previous is not None and canonical_json(previous) != canonical_json(
            expected
        ):
            raise MaintenanceError(_EVIDENCE_CONFLICT)
        if not evidence.ready:
            _deadline(self.deadline)
            _publish_pin(
                self.root, self.target, evidence.store_id, evidence.checksum, "ready"
            )
        if evidence.journal is None or evidence.journal["state"] != "ready":
            self.journal(evidence, "ready", checksum)
        if previous is None:
            _deadline(self.deadline)
            _atomic(report, expected)

    def run(
        self,
        operation: Literal["apply", "resume"],
        descriptors: dict[str, str],
        generations: dict[str, tuple[str, ...]],
        released_generation: Callable[[], str],
    ) -> str:
        target_gate = storage_identity_gate(self.root)
        binding_gate = project_event_binding_path(self.binding.project_root)
        owner = prepare_registry_owner()
        with project_event_operation_intent(
            _intent(self.root), owner, deadline=self.deadline
        ):
            with ExitStack() as witness:
                with _wait(target_gate, self.deadline, _TARGET_UNKNOWN):
                    evidence = self.discover()
                    if evidence is None and operation == "resume":
                        raise MaintenanceError(_PLAN_MISSING)
                    if evidence is not None:
                        _authentic_plan(
                            evidence.plan, descriptors, generations, released_generation
                        )
                    ready = evidence is not None and evidence.ready
                    scan = witness.enter_context(self.scan(parity=not ready))
                    require_imported_history(self.target, self.driver)
                    checksum = None
                    if ready and evidence is not None:
                        if scan.facts["store_id"] != evidence.store_id:
                            raise MaintenanceError("storage_identity_conflict")
                        checksum = self.backup_checksum(evidence)
                    elif evidence is not None:
                        _require_parity(evidence, scan.facts)
                        if evidence.slot is None and scan.facts["store_id"] is not None:
                            raise MaintenanceError("storage_pin_missing")
                    elif scan.facts["store_id"] is not None:
                        raise MaintenanceError("storage_pin_missing")

                with _publication_guards(
                    self.context, target_gate, binding_gate, owner, self.deadline
                ):
                    self.authorize()
                    require_imported_history(self.target, self.driver)
                    if self.discover() != evidence:
                        raise MaintenanceError(_EVIDENCE_CONFLICT)
                    scan.revalidate(self.legacy, self.deadline)
                    _deadline(self.deadline)
                    if evidence is not None and checksum is not None:
                        self.ready(evidence, checksum)
                        return evidence.checksum
                    if evidence is None:
                        evidence = _new_plan(
                            self.target,
                            descriptors[MIGRATION_ID],
                            generations[MIGRATION_ID][0],
                            scan.facts,
                        )
                    if evidence.slot is None:
                        self.pending(evidence)

                # The original witness must remain live across the interval between
                # the pending publication and the target-only backup phase.
                with _wait(target_gate, self.deadline, _TARGET_UNKNOWN):
                    scan.revalidate(self.legacy, self.deadline)
                    pending = self.discover()
                    if (
                        pending is None
                        or pending.data != evidence.data
                        or pending.ready
                        or pending.slot is None
                    ):
                        raise MaintenanceError(_EVIDENCE_CONFLICT)
                    checksum = self.apply_identity(pending, scan.facts, binding_gate)
                    final_scan = witness.enter_context(self.scan(parity=True))
                    _require_parity(pending, final_scan.facts)
                    if final_scan.facts["store_id"] != pending.store_id:
                        raise MaintenanceError("storage_identity_conflict")
                    self.journal(pending, "verified", checksum)
                    verified = self.discover()

                with _publication_guards(
                    self.context, target_gate, binding_gate, owner, self.deadline
                ):
                    self.authorize()
                    require_imported_history(self.target, self.driver)
                    if (
                        verified is None
                        or verified.data != pending.data
                        or verified.slot != pending.slot
                        or verified.journal is None
                        or verified.journal["state"] != "verified"
                        or verified.journal["backup_manifest_checksum"] != checksum
                        or self.discover() != verified
                    ):
                        raise MaintenanceError(_EVIDENCE_CONFLICT)
                    final_scan.revalidate(self.legacy, self.deadline)
                    self.ready(verified, checksum)
                    return verified.checksum


def run_online_project_event_migration(
    *,
    project_root: Path,
    workplace_root: Path,
    device_config_path: Path,
    configuration: ConfigurationProvider,
    operation: Literal["apply", "resume"],
    deadline: float | None = None,
    expected_target: StoreTarget | None = None,
) -> JsonObject:
    """Apply or resume one journal under the caller's native operation lease.

    The host supplies the selected roots and effective configuration. The
    deadline is an absolute monotonic timestamp, defaulting to 30 seconds.
    A host-selected target stays pinned if enrollment changes during dispatch.
    """
    report = StorageMigrationService._report(f"storage-{operation}")
    report["requested_target"] = {"kind": "events", "scope": "project"}
    if expected_target is not None:
        report["selected_target"] = _target_facts(expected_target)
    stop = time.monotonic() + 30.0 if deadline is None else deadline
    try:
        _deadline(stop)
        if operation not in ("apply", "resume"):
            raise MaintenanceError("storage_operation_invalid")
        project_root = _safe(project_root).resolve(strict=True)
        workplace_root = _safe(workplace_root).resolve(strict=True)
        device_config_path = _safe(device_config_path).resolve()
        flow = ProjectMetadataReader(project_root).flow_root()
        if not _safe(flow / _EVENT_PATH).is_file():
            raise MaintenanceError("storage_project_event_journal_missing")
        binding = read_project_event_binding(project_root)
        target = StoreTarget(
            "events", binding.event_target, _EVENT_PATH, "project", binding.project_id
        )
        if expected_target is not None and target != expected_target:
            raise MaintenanceError("storage_enrollment_conflict")
        report["selected_target"] = _target_facts(target)
        report["phase"] = "events"
        if binding.workplace_manifest != workplace_root / "workplace.yaml":
            raise MaintenanceError("storage_enrollment_conflict")
        context = StorageMigrationContext(
            project_root, workplace_root, device_config_path, (target,)
        )
        if _admission_held(context):
            raise MaintenanceError("storage_activity_unknown")
        snapshot = configuration.snapshot()
        if snapshot.errors:
            raise MaintenanceError("storage_configuration_invalid")
        config = snapshot.config
        root = storage_owner_root(context, target)
        legacy = _descriptor()
        if _hash(legacy) != _V1_DESCRIPTOR:
            raise MaintenanceError("storage_transform_changed")
        descriptors = {
            V1_MIGRATION_ID: _V1_DESCRIPTOR,
            MIGRATION_ID: _hash(_online_descriptor()),
        }
        effective = config.to_dict()
        generations: dict[str, tuple[str, ...]] = {
            V1_MIGRATION_ID: (_generation("project_events_v1", context, effective),),
            MIGRATION_ID: (_generation("project_events_v2", context, effective),),
        }

        def released_generation() -> str:
            _, main, _ = _execution_profile(config.database)
            return _generation(
                "operator_offline", _full_context(context, root, main), effective
            )

        require_compatible_runtime(workplace_root)
        coordinator = _Coordinator(
            context,
            binding,
            root,
            target,
            DatabaseFactory.resolve_driver(config.database),
            legacy,
            stop,
        )
        checksum = coordinator.run(
            operation, descriptors, generations, released_generation
        )
        report["targets"].append(
            {
                "kind": "events",
                "scope": "project",
                "target_relative_path": target.target_relative_path,
                "state": "ready",
                "plan_checksum": checksum,
            }
        )
        report["per_target_counts"]["ready"] = 1
        report.update(status="ready", phase="ready")
    except (DatabaseError, ExecutionError, OSError, ValueError, sqlite3.Error) as error:
        StorageMigrationService._failure(report, error)
        if report["error"]["code"] in {
            PROJECT_EVENT_MAINTENANCE_BUSY,
            "storage_deadline_exceeded",
            "storage_project_event_runtime_unknown",
        }:
            report["retryable"] = True
    return report
