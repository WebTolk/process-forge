"""Deterministic, fenced latest-snapshot import with one SQL authority cutover.

Imports and construction are cold. Native host composition supplies actual
ownership/tree proof; a CLI flag cannot manufacture it. This module does not
start services, discover projects or perform automatic UUID adoption.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

from ..database import (
    Database,
    DatabaseTarget,
    SchemaDefinition,
    SchemaManager,
    SqlSession,
    SqlStatement,
)
from ..database.errors import DatabaseError
from ..executions.model import ExecutionError, ExecutionKey, ExecutionRecord
from ..executions.projection import canonical_json
from ..executions.schema import EXECUTION_SCHEMA
from ..executions.sqlite_repository import SQLiteExecutionRepository
from ..project.metadata import ProjectMetadataReader
from ..runtime.execution_admission import ExecutionAdmission
from .contracts import (
    BackupPort,
    ExecutionMigrationContext,
    ExecutionMigrationVerifier,
    JsonObject,
    MaintenanceError,
    MigrationSafety,
)
from .journal_scan import (
    ExecutionSnapshot,
    _check_links,
    _exclusive_bytes,
    execution_bytes,
    execution_json,
    execution_snapshots,
)

MIGRATION_ID = "r02-worker-executions-v1"
_DDL = (
    "CREATE TABLE execution_migrations(migration_id TEXT PRIMARY KEY,descriptor_checksum TEXT NOT NULL,plan_checksum TEXT NOT NULL,store_id TEXT NOT NULL,source_generation INTEGER NOT NULL CHECK(source_generation>=0),target_generation INTEGER NOT NULL CHECK(target_generation>source_generation),state TEXT NOT NULL CHECK(state IN ('planned','backed_up','importing','verified','ready')),checkpoint INTEGER NOT NULL CHECK(checkpoint>=0),manifest_checksum TEXT NOT NULL,evidence_relative_path TEXT NOT NULL,backup_manifest_checksum TEXT,last_error_code TEXT)",
)


def _digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _hash(value: object) -> str:
    return _digest(canonical_json(value).encode("utf-8"))


EXECUTION_MIGRATION_SCHEMA = SchemaDefinition(
    "execution_migration",
    1,
    _DDL,
    _hash({"namespace": "execution_migration", "version": 1, "statements": _DDL}),
)


def _atomic(path: Path, value: object) -> None:
    """Replace only an owned derived journal/report, with adjacent staging."""
    _check_links(path, "execution_evidence_unsafe")
    temporary = path.with_name("." + path.name + "." + uuid4().hex)
    try:
        with temporary.open("xb") as handle:
            handle.write((canonical_json(value) + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read(path: Path) -> JsonObject:
    return execution_json(execution_bytes(path))


def _ordered_inventory(
    project: Path, flow: Path, project_id: str, skip: bool
) -> Iterator[tuple[JsonObject, ExecutionSnapshot | None, bytes | None]]:
    """Stream globally ordered UTF-8 paths with bounded directory-name selection.

    This includes directory-name and receipt facts; prefix names are ordered by
    the full relative path, not by locale or directory traversal order.
    """
    yield from execution_snapshots(
        project, flow, project_id, skip_terminal_invalid=skip
    )


class ExecutionMigrationService:
    """Import only with explicit targets, verified backup and live host proof.

    safety is the private proof-port extension authorized for W4. workplace_root
    pins host-selected enrollment; the verifier must refuse a mismatch. Profile
    routing is project_main; a differently selected profile needs host composition
    to provide a matching engine/binding contract before use.
    """

    def __init__(
        self,
        *,
        database: Database,
        repository: SQLiteExecutionRepository,
        admission: ExecutionAdmission,
        backup: BackupPort,
        safety: ExecutionMigrationVerifier | None = None,
        workplace_root: Path | None = None,
        profile_id: str = "project_main",
    ) -> None:
        self.database = database
        self.repository = repository
        self.admission = admission
        self.backup = backup
        self.safety = safety
        self.workplace_root = workplace_root
        self.profile_id = profile_id

    def _pins(self, project_root: Path) -> tuple[Path, Path, str, str]:
        project = Path(project_root).absolute()
        if ".." in Path(project_root).parts:
            raise MaintenanceError("execution_path_unsafe")
        _check_links(project, "execution_path_unsafe")
        metadata = ProjectMetadataReader(project)
        flow = metadata.flow_root()
        _check_links(flow / "process-forge.yaml", "execution_path_unsafe")
        manifest = metadata.manifest()
        owner = manifest.get("project")
        project_id = owner.get("id") if isinstance(owner, dict) else None
        if (
            not isinstance(project_id, str)
            or not project_id.strip()
            or "\x00" in project_id
        ):
            raise MaintenanceError("project_identity_required")
        target = self.database.target
        _check_links(target.path, "execution_path_unsafe")
        if (
            target.identity.owner_id != project_id
            or target.identity.scope != "project"
            or target.identity.store_id is None
            or self.repository.project_id != project_id
            or self.repository.database is not self.database
        ):
            raise MaintenanceError("execution_identity_conflict")
        try:
            relative = target.path.relative_to(flow).as_posix()
        except ValueError:
            raise MaintenanceError("execution_target_unsafe") from None
        if any(part in {"", ".", ".."} for part in relative.split("/")):
            raise MaintenanceError("execution_target_unsafe")
        return project, flow, project_id, relative

    @staticmethod
    def _descriptor() -> JsonObject:
        root = Path(__file__).absolute().parents[3]
        descriptor = _read(root / "schemas/execution-migration-v1.json")
        expected = {
            "migration_id": MIGRATION_ID,
            "descriptor_version": 1,
            "source_format": "worker-status-json",
            "source_schema_versions": [1],
            "target_namespace": "execution",
            "from_schema_version": 0,
            "to_schema_version": 1,
            "min_reader_capability": "execution-storage-v1",
            "min_writer_capability": "execution-storage-v1",
            "target_schema_checksum": EXECUTION_SCHEMA.checksum,
        }
        files = descriptor.get("transform_files")
        paths = (
            "src/processforge_core/maintenance/contracts.py",
            "src/processforge_core/maintenance/execution_migration.py",
            "src/processforge_core/maintenance/journal_scan.py",
            "src/processforge_core/executions/schema.py",
            "src/processforge_core/executions/sqlite_repository.py",
        )
        actual = [
            {"relative_path": path, "sha256": _digest((root / path).read_bytes())}
            for path in paths
        ]
        if (
            any(descriptor.get(k) != v for k, v in expected.items())
            or files != actual
            or descriptor.get("transform_checksum") != _hash(actual)
            or set(descriptor)
            != set(expected) | {"transform_files", "transform_checksum"}
        ):
            raise MaintenanceError("execution_transform_changed")
        return descriptor

    def _proof(
        self,
        project: Path,
        plan: Mapping[str, object],
        phase: Literal["inspect", "freeze", "resume", "cutover"],
    ) -> MigrationSafety:
        if self.safety is None:
            raise MaintenanceError("execution_safety_unavailable")
        context = ExecutionMigrationContext(
            project,
            self.workplace_root,
            str(plan["project_id"]),
            str(plan["store_id"]),
            str(plan["target_relative_path"]),
            int(cast(int, plan["source_generation"])),
            int(cast(int, plan["target_generation"])),
            str(plan.get("plan_checksum", "")),
            str(plan["manifest_checksum"]),
            phase,
        )
        try:
            proof = self.safety(context)
        except Exception:
            raise MaintenanceError("execution_safety_unavailable") from None
        if (
            not isinstance(proof, MigrationSafety)
            or proof.state != "proven"
            or not isinstance(proof.generation, str)
            or not proof.generation.strip()
            or type(proof.evidence) is not tuple
            or not proof.evidence
            or any(
                not isinstance(item, str) or not item.strip() for item in proof.evidence
            )
        ):
            raise MaintenanceError("execution_activity_unknown")
        expected = plan.get("safety_generation")
        if expected is not None and proof.generation != expected:
            raise MaintenanceError("execution_safety_changed")
        return proof

    @staticmethod
    def _evidence(project: Path, flow: Path, evidence: Path) -> Path:
        directory = Path(evidence).absolute()
        if ".." in Path(evidence).parts:
            raise MaintenanceError("execution_evidence_unsafe")
        _check_links(directory, "execution_evidence_unsafe")
        base = flow / "maintenance"
        if not directory.is_relative_to(base) or directory == base:
            raise MaintenanceError("execution_evidence_unsafe")
        # No source/output directory is accepted as maintenance evidence.
        directory.relative_to(project)
        return directory

    def _scan(
        self,
        project: Path,
        flow: Path,
        project_id: str,
        skip: bool,
        evidence: Path | None = None,
    ) -> JsonObject:
        digest = hashlib.sha256()
        counts = {
            "snapshots": 0,
            "imported": 0,
            "skipped": 0,
            "inventory": 0,
            "directories": 0,
            "floor_only": 0,
            "import_units": 0,
        }
        temporary: Path | None = None
        handle = None
        if evidence is not None:
            (evidence / "sources").mkdir(parents=True, exist_ok=True)
            temporary = evidence / (".manifest." + uuid4().hex)
            handle = temporary.open("xb")
        try:
            for fact, snapshot, raw in _ordered_inventory(
                project, flow, project_id, skip
            ):
                encoded = (canonical_json(fact) + "\n").encode("utf-8")
                digest.update(encoded)
                counts["inventory"] += 1
                if "directory" in fact or "missing_status" in fact:
                    counts["directories"] += 1
                if snapshot is not None:
                    counts["snapshots"] += 1
                    counts[
                        "skipped" if snapshot.invalid_historical else "imported"
                    ] += 1
                if "allocation_floor" in fact:
                    counts["import_units"] += 1
                    if snapshot is None or snapshot.invalid_historical:
                        counts["floor_only"] += 1
                if handle is not None:
                    assert evidence is not None
                    handle.write(encoded)
                    if raw is not None:
                        _exclusive_bytes(
                            evidence / "sources" / str(fact["sha256"])[7:], raw
                        )
            if handle is not None:
                assert evidence is not None and temporary is not None
                handle.flush()
                os.fsync(handle.fileno())
                handle.close()
                manifest = evidence / "manifest.ndjson"
                if manifest.exists():
                    if self._file_digest(manifest) != "sha256:" + digest.hexdigest():
                        raise MaintenanceError("execution_manifest_changed")
                else:
                    # Frozen manifest is immutable; no replacement of another plan.
                    with (
                        manifest.open("xb") as destination,
                        temporary.open("rb") as source,
                    ):
                        while chunk := source.read(1048576):
                            destination.write(chunk)
                        destination.flush()
                        os.fsync(destination.fileno())
        finally:
            if handle is not None:
                handle.close()
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return {"manifest_checksum": "sha256:" + digest.hexdigest(), "counts": counts}

    @staticmethod
    def _file_digest(path: Path) -> str:
        _check_links(path, "execution_evidence_unsafe")
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1048576):
                digest.update(chunk)
        return "sha256:" + digest.hexdigest()

    def inspect(
        self, project_root: Path, *, evidence_dir: Path | None = None
    ) -> JsonObject:
        """Read-only plan inspection, optionally retaining explicit scan evidence."""
        result = self.plan(project_root, evidence_dir=evidence_dir)
        return {**result, "operation": "execution-inspect"}

    def plan(
        self,
        project_root: Path,
        *,
        skip_terminal_invalid: bool = False,
        evidence_dir: Path | None = None,
    ) -> JsonObject:
        """Pin exact transform, identity and streaming manifest without DDL/binding."""
        try:
            project, flow, project_id, relative = self._pins(project_root)
            binding = flow / "data/execution-storage.json"
            _check_links(binding, "execution_path_unsafe")
            if binding.exists():
                raise MaintenanceError("execution_resume_required")
            descriptor = self._descriptor()
            status = SchemaManager().inspect(
                self.database, (EXECUTION_SCHEMA, EXECUTION_MIGRATION_SCHEMA)
            )
            if status.state == "unsupported" or any(
                ns in {"execution", "execution_migration"}
                for ns, _, _ in status.versions
            ):
                raise MaintenanceError("execution_storage_not_ready")
            evidence = (
                self._evidence(project, flow, evidence_dir)
                if evidence_dir is not None
                else None
            )
            scan = self._scan(
                project, flow, project_id, skip_terminal_invalid, evidence
            )
            result: JsonObject = {
                "schema_version": 1,
                "operation": "execution-import",
                "status": "planned",
                "blocked": False,
                "migration_id": MIGRATION_ID,
                "phase": "planned",
                "checkpoint": 0,
                "authority": "legacy",
                "active_coverage": "unknown",
                "history_complete": False,
                "project_id": project_id,
                "store_id": self.database.target.identity.store_id,
                "target_relative_path": relative,
                "source_generation": 0,
                "target_generation": 1,
                "target_existed": status.state != "missing",
                "original_versions": [list(v) for v in status.versions],
                "descriptor_checksum": _hash(descriptor),
                "target_schema_checksum": EXECUTION_SCHEMA.checksum,
                "migration_schema_checksum": EXECUTION_MIGRATION_SCHEMA.checksum,
                "skip_terminal_invalid": skip_terminal_invalid,
                **scan,
                "error": None,
                "evidence": [],
            }
            proof = self._proof(project, result, "inspect")
            result["safety_generation"] = proof.generation
            result["plan_checksum"] = self._plan_hash(result)
            result["active_coverage"] = "complete"
            return result
        except (MaintenanceError, DatabaseError, ExecutionError) as error:
            return self._failure("execution-import", error.code)
        except (OSError, ValueError, TypeError, KeyError, SystemExit):
            return self._failure("execution-import", "execution_input_invalid")

    @staticmethod
    def _plan_hash(plan: Mapping[str, object]) -> str:
        keys = (
            "migration_id",
            "project_id",
            "store_id",
            "target_relative_path",
            "source_generation",
            "target_generation",
            "descriptor_checksum",
            "target_schema_checksum",
            "migration_schema_checksum",
            "manifest_checksum",
            "skip_terminal_invalid",
            "safety_generation",
            "target_existed",
            "original_versions",
            "counts",
        )
        return _hash({key: plan[key] for key in keys})

    def _validate(
        self,
        project: Path,
        flow: Path,
        project_id: str,
        relative: str,
        plan: Mapping[str, object],
        evidence: Path,
    ) -> None:
        if (
            plan.get("migration_id") != MIGRATION_ID
            or plan.get("project_id") != project_id
            or plan.get("store_id") != self.database.target.identity.store_id
            or plan.get("target_relative_path") != relative
            or plan.get("source_generation") != 0
            or plan.get("target_generation") != 1
            or type(plan.get("skip_terminal_invalid")) is not bool
            or plan.get("descriptor_checksum") != _hash(self._descriptor())
            or plan.get("target_schema_checksum") != EXECUTION_SCHEMA.checksum
            or plan.get("migration_schema_checksum")
            != EXECUTION_MIGRATION_SCHEMA.checksum
            or plan.get("plan_checksum") != self._plan_hash(plan)
        ):
            raise MaintenanceError("execution_plan_changed")
        if self._file_digest(evidence / "manifest.ndjson") != plan["manifest_checksum"]:
            raise MaintenanceError("execution_manifest_changed")

    def _binding(self, plan: Mapping[str, object]) -> JsonObject:
        return {
            "schema_version": 1,
            "project_id": plan["project_id"],
            "store_id": plan["store_id"],
            "profile_id": self.profile_id,
            "target_relative_path": plan["target_relative_path"],
        }

    def apply(
        self,
        project_root: Path,
        plan: Mapping[str, object],
        *,
        evidence_dir: Path,
        offline_confirmed: bool = False,
    ) -> JsonObject:
        """Freeze under admission; import/checkpoint; revalidate and cut over once."""
        return self._execute(
            project_root, plan, evidence_dir, offline_confirmed, resume=False
        )

    def resume(
        self,
        project_root: Path,
        *,
        migration_id: str,
        plan_checksum: str,
        evidence_dir: Path,
        offline_confirmed: bool = False,
    ) -> JsonObject:
        """Select exact durable plan; never choose newest evidence or a new backup."""
        try:
            project, flow, _, _ = self._pins(project_root)
            evidence = self._evidence(project, flow, evidence_dir)
            plan = _read(evidence / "plan.json")
            if (
                migration_id != MIGRATION_ID
                or plan.get("plan_checksum") != plan_checksum
            ):
                raise MaintenanceError("execution_plan_changed")
            return self._execute(
                project_root, plan, evidence, offline_confirmed, resume=True
            )
        except (MaintenanceError, DatabaseError, ExecutionError) as error:
            return self._failure("execution-resume", error.code)
        except (OSError, ValueError, TypeError, KeyError, SystemExit):
            return self._failure("execution-resume", "execution_input_invalid")

    def abort(
        self,
        project_root: Path,
        *,
        plan_checksum: str,
        evidence_dir: Path,
        offline_confirmed: bool = False,
    ) -> JsonObject:
        """Remove only our pending binding before any target/schema mutation.

        Once namespace/import commits exist, explicit roll-forward is required.
        This conservative abort never drops shared schemas or restores in place.
        """
        try:
            if offline_confirmed is not True:
                raise MaintenanceError("execution_offline_confirmation_required")
            project, flow, project_id, relative = self._pins(project_root)
            evidence = self._evidence(project, flow, evidence_dir)
            plan = _read(evidence / "plan.json")
            self._validate(project, flow, project_id, relative, plan, evidence)
            if plan["plan_checksum"] != plan_checksum:
                raise MaintenanceError("execution_plan_changed")
            with self.admission.maintenance(project, self.workplace_root):
                self._proof(project, plan, "resume")
                self._unchanged(project, flow, project_id, plan)
                status = SchemaManager().inspect(self.database, ())
                if (
                    any(
                        ns in {"execution", "execution_migration"}
                        for ns, _, _ in status.versions
                    )
                    or (status.state != "missing") != plan["target_existed"]
                    or [list(v) for v in status.versions] != plan["original_versions"]
                ):
                    raise MaintenanceError("execution_abort_unsafe")
                binding = flow / "data/execution-storage.json"
                if _read(binding) != self._binding(plan):
                    raise MaintenanceError("execution_binding_conflict")
                binding.unlink()
            return {
                "schema_version": 1,
                "operation": "execution-abort",
                "status": "planned",
                "blocked": False,
                "phase": "aborted",
                "authority": "legacy",
                "error": None,
                "evidence": [evidence.relative_to(project).as_posix()],
            }
        except (MaintenanceError, DatabaseError, ExecutionError) as error:
            return self._failure("execution-abort", error.code)
        except (OSError, ValueError, TypeError, KeyError, SystemExit):
            return self._failure("execution-abort", "execution_input_invalid")

    def _execute(
        self,
        project_root: Path,
        plan: Mapping[str, object],
        evidence_dir: Path,
        offline: bool,
        *,
        resume: bool,
    ) -> JsonObject:
        operation = "execution-resume" if resume else "execution-import"
        try:
            if offline is not True:
                raise MaintenanceError("execution_offline_confirmation_required")
            project, flow, project_id, relative = self._pins(project_root)
            evidence = self._evidence(project, flow, evidence_dir)
            if plan.get("blocked") or plan.get("plan_checksum") != self._plan_hash(
                plan
            ):
                raise MaintenanceError("execution_plan_changed")
            binding = flow / "data/execution-storage.json"
            if not resume:
                # Large scan/copy runs outside admission and all SQL sessions.
                # After publishing freeze, recheck live inventory before mutation.
                scan = self._scan(
                    project,
                    flow,
                    project_id,
                    bool(plan["skip_terminal_invalid"]),
                    evidence,
                )
                if (
                    scan["manifest_checksum"] != plan["manifest_checksum"]
                    or scan["counts"] != plan["counts"]
                ):
                    raise MaintenanceError("execution_manifest_changed")
                self._validate(project, flow, project_id, relative, plan, evidence)
                _exclusive_bytes(
                    evidence / "plan.json",
                    (canonical_json(dict(plan)) + "\n").encode("utf-8"),
                )
            else:
                self._validate(project, flow, project_id, relative, plan, evidence)
            with self.admission.maintenance(project, self.workplace_root):
                # Validate source pins before publishing the pending routing fence.
                self._proof(project, plan, "resume" if resume else "freeze")
                if binding.exists() and _read(binding) != self._binding(plan):
                    raise MaintenanceError("execution_binding_conflict")
                if resume and not binding.exists():
                    raise MaintenanceError("execution_binding_missing")
                if not resume and binding.exists():
                    raise MaintenanceError("execution_resume_required")
                if not resume:
                    binding.parent.mkdir(parents=True, exist_ok=True)
                    _exclusive_bytes(
                        binding,
                        (canonical_json(self._binding(plan)) + "\n").encode("utf-8"),
                    )
            self._validate(project, flow, project_id, relative, plan, evidence)
            # SQL committed marker wins over any stale post-commit file report.
            if self._ready(plan, evidence, project):
                return self._publish(operation, plan, evidence, project)
            self._unchanged(project, flow, project_id, plan)
            journal = self._backup(plan, evidence)
            self._initialize(plan, evidence, project, journal)
            self._import(plan, evidence)
            self._verify(plan, evidence)
            with self.admission.maintenance(project, self.workplace_root):
                if _read(binding) != self._binding(plan):
                    raise MaintenanceError("execution_binding_conflict")
                self._unchanged(project, flow, project_id, plan)
                if self._pins(project) != (project, flow, project_id, relative):
                    raise MaintenanceError("execution_identity_conflict")
                self._proof(project, plan, "cutover")
                self._cutover(plan)
            return self._publish(operation, plan, evidence, project)
        except (MaintenanceError, DatabaseError, ExecutionError) as error:
            return self._failure(operation, error.code)
        except (OSError, ValueError, TypeError, KeyError, SystemExit):
            return self._failure(operation, "execution_input_invalid")

    def _unchanged(
        self, project: Path, flow: Path, project_id: str, plan: Mapping[str, object]
    ) -> None:
        current = self._scan(
            project, flow, project_id, bool(plan["skip_terminal_invalid"])
        )
        if (
            current["manifest_checksum"] != plan["manifest_checksum"]
            or current["counts"] != plan["counts"]
        ):
            raise MaintenanceError("execution_manifest_changed")

    def _backup(self, plan: Mapping[str, object], evidence: Path) -> JsonObject:
        journal_path = evidence / "journal.json"
        journal = (
            _read(journal_path)
            if journal_path.exists()
            else {
                "plan_checksum": plan["plan_checksum"],
                "store_id": plan["store_id"],
                "state": "planned",
                "target_existed": plan["target_existed"],
                "backup_manifest_checksum": None,
            }
        )
        if (
            journal.get("plan_checksum") != plan["plan_checksum"]
            or journal.get("store_id") != plan["store_id"]
            or journal.get("target_existed") != plan["target_existed"]
        ):
            raise MaintenanceError("execution_backup_conflict")
        bundle = evidence / "backup"
        if plan["target_existed"]:
            if not bundle.exists():
                if journal["state"] != "planned":
                    raise MaintenanceError("execution_backup_missing")
                status = SchemaManager().inspect(self.database, ())
                if [list(v) for v in status.versions] != plan["original_versions"]:
                    raise MaintenanceError("execution_target_changed")
                self.backup.create(self.database.target.path, bundle)
            verified = self.backup.verify(bundle)
            if verified.get("verified") is not True:
                raise MaintenanceError("execution_backup_unverified")
            checksum = self._file_digest(bundle / "manifest.json")
            if journal["backup_manifest_checksum"] not in (None, checksum):
                raise MaintenanceError("execution_backup_changed")
            copied = Database(
                self.database.driver,
                DatabaseTarget(
                    bundle / "database.sqlite3", self.database.target.identity
                ),
            )
            status = SchemaManager().inspect(copied, ())
            if [list(v) for v in status.versions] != plan["original_versions"]:
                raise MaintenanceError("execution_backup_conflict")
            journal["backup_manifest_checksum"] = checksum
        elif journal["state"] == "planned" and self.database.target.path.exists():
            raise MaintenanceError("execution_target_changed")
        if journal["state"] == "planned":
            journal["state"] = "backed_up"
            _atomic(journal_path, journal)
        return journal

    def _initialize(
        self,
        plan: Mapping[str, object],
        evidence: Path,
        project: Path,
        journal: JsonObject,
    ) -> None:
        manager = SchemaManager()
        requirements = (EXECUTION_SCHEMA, EXECUTION_MIGRATION_SCHEMA)
        status = manager.inspect(self.database, requirements)
        if status.state == "missing":
            if plan["target_existed"]:
                raise MaintenanceError("execution_target_changed")
            manager.initialize(self.database, requirements)
        elif status.state == "migration_required":
            manager.apply(self.database, requirements)
        elif status.state != "ready":
            raise MaintenanceError("execution_storage_not_ready")
        with self.database.transaction() as session:
            state = session.fetch_one(
                SqlStatement(
                    "SELECT project_id,generation,authority,readiness,migration_id,plan_checksum FROM execution_state WHERE singleton=1"
                )
            )
            if state is None:
                session.execute(
                    SqlStatement(
                        "INSERT INTO execution_state VALUES(1,?,0,'legacy','importing','unknown',0,1,?,?)",
                        (
                            str(plan["project_id"]),
                            MIGRATION_ID,
                            str(plan["plan_checksum"]),
                        ),
                    )
                )
            elif state.values != (
                plan["project_id"],
                0,
                "legacy",
                "importing",
                MIGRATION_ID,
                plan["plan_checksum"],
            ):
                raise MaintenanceError("execution_state_conflict")
            migration = self._marker(session)
            if migration is None:
                session.execute(
                    SqlStatement(
                        "INSERT INTO execution_migrations VALUES(?,?,?,?,0,1,'importing',0,?,?,?,NULL)",
                        (
                            MIGRATION_ID,
                            str(plan["descriptor_checksum"]),
                            str(plan["plan_checksum"]),
                            str(plan["store_id"]),
                            str(plan["manifest_checksum"]),
                            evidence.relative_to(project).as_posix(),
                            cast(str | None, journal["backup_manifest_checksum"]),
                        ),
                    )
                )
            else:
                self._check_marker(
                    migration,
                    plan,
                    evidence,
                    project,
                    journal["backup_manifest_checksum"],
                )
        journal["state"] = "importing"
        _atomic(evidence / "journal.json", journal)

    @staticmethod
    def _marker(session: SqlSession) -> JsonObject | None:
        row = session.fetch_one(
            SqlStatement(
                "SELECT descriptor_checksum,plan_checksum,store_id,source_generation,target_generation,state,checkpoint,manifest_checksum,evidence_relative_path,backup_manifest_checksum FROM execution_migrations WHERE migration_id=?",
                (MIGRATION_ID,),
            )
        )
        return (
            dict(zip(row.columns, row.values, strict=True)) if row is not None else None
        )

    @staticmethod
    def _check_marker(
        marker: Mapping[str, object],
        plan: Mapping[str, object],
        evidence: Path,
        project: Path,
        backup_checksum: object,
    ) -> None:
        for key in (
            "descriptor_checksum",
            "plan_checksum",
            "store_id",
            "source_generation",
            "target_generation",
            "manifest_checksum",
        ):
            if marker.get(key) != plan[key]:
                raise MaintenanceError("execution_checkpoint_conflict")
        if (
            marker.get("evidence_relative_path")
            != evidence.relative_to(project).as_posix()
            or marker.get("backup_manifest_checksum") != backup_checksum
        ):
            raise MaintenanceError("execution_checkpoint_conflict")

    def _batches(
        self, plan: Mapping[str, object], evidence: Path
    ) -> Iterator[
        tuple[
            int,
            tuple[ExecutionRecord, ...],
            tuple[tuple[str, str, str], ...],
            tuple[tuple[str, str, int], ...],
        ]
    ]:
        # Each unit has exactly one allocation fact and zero or one snapshot.
        # Thus both lists and the combined unit count stay <=256, including a
        # batch containing no ExecutionRecord at all.
        records: list[ExecutionRecord] = []
        facts: list[tuple[str, str, str]] = []
        floors: list[tuple[str, str, int]] = []
        position = 0
        with (evidence / "manifest.ndjson").open("rb") as manifest:
            while line := manifest.readline(65537):
                if len(line) > 65536:
                    raise MaintenanceError("execution_manifest_invalid")
                item = execution_json(line)
                raw = None
                if "relative_path" in item:
                    raw = execution_bytes(
                        evidence / "sources" / str(item["sha256"])[7:]
                    )
                    if _digest(raw) != item["sha256"] or len(raw) != item["size"]:
                        raise MaintenanceError("execution_source_changed")
                floor = item.get("allocation_floor")
                if floor is None:
                    continue
                if not isinstance(floor, dict):
                    raise MaintenanceError("execution_manifest_invalid")
                key = ExecutionKey(
                    str(plan["project_id"]),
                    floor["run_id"],
                    floor["task_id"],
                    floor["next_attempt"],
                )
                if "semantic_checksum" in item:
                    if raw is None:
                        raise MaintenanceError("execution_manifest_invalid")
                    payload = execution_json(raw)
                    if _hash(payload) != item["semantic_checksum"]:
                        raise MaintenanceError("execution_source_changed")
                    snapshot_key = ExecutionKey(
                        str(plan["project_id"]),
                        payload["run_id"],
                        payload["task_id"],
                        payload["attempt"],
                    )
                    if (
                        key.run_id != snapshot_key.run_id
                        or key.task_id != snapshot_key.task_id
                        or key.attempt != item["next_attempt"]
                        or key.attempt <= snapshot_key.attempt
                    ):
                        raise MaintenanceError("execution_manifest_invalid")
                    if not item["skipped"]:
                        snapshot = ExecutionSnapshot(
                            str(item["relative_path"]),
                            raw,
                            payload,
                            snapshot_key,
                            key.attempt,
                            False,
                        )
                        records.append(
                            snapshot.record(int(cast(int, plan["target_generation"])))
                        )
                        facts.append(
                            (
                                snapshot.relative_path,
                                item["sha256"],
                                item["semantic_checksum"],
                            )
                        )
                floors.append((key.run_id, key.task_id, key.attempt))
                position += 1
                if len(floors) == 256:
                    yield position, tuple(records), tuple(facts), tuple(floors)
                    records, facts, floors = [], [], []
        if floors:
            yield position, tuple(records), tuple(facts), tuple(floors)

    def _import(self, plan: Mapping[str, object], evidence: Path) -> None:
        for position, records, facts, floors in self._batches(plan, evidence):
            with self.database.transaction() as session:
                marker = self._marker(session)
                if (
                    marker is None
                    or marker["plan_checksum"] != plan["plan_checksum"]
                    or marker["state"] not in {"importing", "verified"}
                ):
                    raise MaintenanceError("execution_checkpoint_conflict")
                checkpoint = int(marker["checkpoint"])
                if position <= checkpoint:
                    continue
                if position - len(floors) != checkpoint:
                    raise MaintenanceError("execution_checkpoint_conflict")
                self.repository.import_legacy(
                    session, records, source_facts=facts, next_attempt_floors=floors
                )
                changed = session.execute(
                    SqlStatement(
                        "UPDATE execution_migrations SET checkpoint=?,state='importing' WHERE migration_id=? AND checkpoint=? AND plan_checksum=?",
                        (
                            position,
                            MIGRATION_ID,
                            checkpoint,
                            str(plan["plan_checksum"]),
                        ),
                    )
                )
                if changed.affected_rows != 1:
                    raise MaintenanceError("execution_checkpoint_conflict")

    def _verify(self, plan: Mapping[str, object], evidence: Path) -> None:
        if (
            SchemaManager()
            .inspect(self.database, (EXECUTION_SCHEMA, EXECUTION_MIGRATION_SCHEMA))
            .state
            != "ready"
        ):
            raise MaintenanceError("execution_schema_invalid")
        total = units = 0
        for position, records, facts, floors in self._batches(plan, evidence):
            # Check before replay: a missing/lowered floor must fail rather than
            # be silently repaired by monotonic UPSERT during verification.
            with self.database.transaction() as session:
                for run_id, task_id, floor in floors:
                    params = (str(plan["project_id"]), run_id, task_id)
                    head = session.fetch_one(
                        SqlStatement(
                            "SELECT next_attempt FROM execution_heads WHERE project_id=? AND run_id=? AND task_id=?",
                            params,
                        )
                    )
                    saved = session.fetch_one(
                        SqlStatement(
                            "SELECT next_attempt FROM execution_allocation_floors WHERE project_id=? AND run_id=? AND task_id=?",
                            params,
                        )
                    )
                    if (
                        head is not None and (head[0] != floor or saved is not None)
                    ) or (head is None and (saved is None or saved[0] != floor)):
                        raise MaintenanceError("execution_floor_verification_failed")
                inserted, replayed = self.repository.import_legacy(
                    session, records, source_facts=facts, next_attempt_floors=floors
                )
                if inserted != 0 or replayed != len(records):
                    raise MaintenanceError("execution_replay_failed")
                total += replayed
                units = position
        counts = cast(Mapping[str, int], plan["counts"])
        expected = counts["imported"]
        with self.database.transaction() as session:
            for statement in (
                *EXECUTION_SCHEMA.statements,
                *EXECUTION_MIGRATION_SCHEMA.statements,
            ):
                name = statement.split("(", 1)[0].split()[2]
                actual = session.fetch_one(
                    SqlStatement("SELECT sql FROM sqlite_schema WHERE name=?", (name,))
                )
                if actual is None or actual[0] != statement:
                    raise MaintenanceError("execution_schema_invalid")
            # Public sessions prohibit PRAGMA/admin access. Check domain FKs by
            # bounded result joins, then reuse BackupPort for SQLite's physical
            # integrity check on a deterministic WAL-aware verification snapshot.
            foreign = session.fetch_one(
                SqlStatement(
                    "SELECT 1 FROM execution_heads h LEFT JOIN execution_attempts a ON a.project_id=h.project_id AND a.run_id=h.run_id AND a.task_id=h.task_id AND a.attempt=h.latest_attempt WHERE a.attempt IS NULL UNION ALL SELECT 1 FROM execution_receipt_admissions r LEFT JOIN execution_attempts a USING(project_id,run_id,task_id,attempt) WHERE a.attempt IS NULL LIMIT 1"
                )
            )
            current = session.fetch_one(
                SqlStatement("SELECT 1 FROM execution_current LIMIT 1")
            )
            count = session.fetch_one(
                SqlStatement("SELECT count(*) AS total FROM execution_attempts")
            )
            heads = session.fetch_one(
                SqlStatement("SELECT count(*) FROM execution_heads")
            )
            floor_count = session.fetch_one(
                SqlStatement("SELECT count(*) FROM execution_allocation_floors")
            )
            receipts = session.fetch_one(
                SqlStatement("SELECT 1 FROM execution_receipt_admissions LIMIT 1")
            )
            marker = self._marker(session)
            if (
                foreign is not None
                or current is not None
                or count is None
                or count[0] != expected
                or total != expected
                or marker is None
                or marker["checkpoint"] != counts["import_units"]
                or units != counts["import_units"]
                or floor_count is None
                or floor_count[0] != counts["floor_only"]
                or heads is None
                or heads[0] != expected
                or receipts is not None
            ):
                raise MaintenanceError("execution_verification_failed")
            session.execute(
                SqlStatement(
                    "UPDATE execution_migrations SET state='verified' WHERE migration_id=? AND plan_checksum=?",
                    (MIGRATION_ID, str(plan["plan_checksum"])),
                )
            )
        # This is named, code-owned verification evidence, not a replacement of
        # the pre-mutation recovery backup. Resume verifies/reuses the same bytes.
        self._verification_snapshot(evidence, create=True)

    def _verification_snapshot(self, evidence: Path, *, create: bool) -> None:
        """Verify the pinned integrity snapshot; create it only before cutover."""
        snapshot = evidence / "verification"
        journal = _read(evidence / "journal.json")
        if not snapshot.exists():
            if not create or journal.get("verification_manifest_checksum") is not None:
                raise MaintenanceError("execution_verification_missing")
            self.backup.create(self.database.target.path, snapshot)
        verified = self.backup.verify(snapshot)
        if (
            verified.get("verified") is not True
            or verified.get("integrity_check") != "ok"
        ):
            raise MaintenanceError("execution_verification_failed")
        checksum = self._file_digest(snapshot / "manifest.json")
        if journal.get("verification_manifest_checksum") != checksum and (
            not create or journal.get("verification_manifest_checksum") is not None
        ):
            raise MaintenanceError("execution_verification_changed")
        copied = Database(
            self.database.driver,
            DatabaseTarget(
                snapshot / "database.sqlite3", self.database.target.identity
            ),
        )
        if (
            SchemaManager()
            .inspect(copied, (EXECUTION_SCHEMA, EXECUTION_MIGRATION_SCHEMA))
            .state
            != "ready"
        ):
            raise MaintenanceError("execution_verification_failed")
        if create:
            journal.update(state="verified", verification_manifest_checksum=checksum)
            _atomic(evidence / "journal.json", journal)

    def _cutover(self, plan: Mapping[str, object]) -> None:
        with self.database.transaction() as session:
            marker = self._marker(session)
            if (
                marker is None
                or marker["state"] != "verified"
                or marker["plan_checksum"] != plan["plan_checksum"]
                or marker["checkpoint"]
                != cast(Mapping[str, int], plan["counts"])["import_units"]
            ):
                raise MaintenanceError("execution_checkpoint_conflict")
            if (
                session.fetch_one(
                    SqlStatement("SELECT 1 FROM execution_current LIMIT 1")
                )
                is not None
            ):
                raise MaintenanceError("execution_activity_unknown")
            changed = session.execute(
                SqlStatement(
                    "UPDATE execution_state SET generation=1,authority='sql',readiness='ready',active_coverage='complete',revision=revision+1 WHERE singleton=1 AND project_id=? AND generation=0 AND authority='legacy' AND readiness='importing' AND migration_id=? AND plan_checksum=?",
                    (str(plan["project_id"]), MIGRATION_ID, str(plan["plan_checksum"])),
                )
            )
            if changed.affected_rows != 1:
                raise MaintenanceError("execution_cutover_conflict")
            session.execute(
                SqlStatement(
                    "UPDATE execution_migrations SET state='ready' WHERE migration_id=? AND state='verified' AND plan_checksum=?",
                    (MIGRATION_ID, str(plan["plan_checksum"])),
                )
            )

    def _ready(self, plan: Mapping[str, object], evidence: Path, project: Path) -> bool:
        status = SchemaManager().inspect(
            self.database, (EXECUTION_SCHEMA, EXECUTION_MIGRATION_SCHEMA)
        )
        if status.state != "ready":
            return False
        with self.database.read() as session:
            marker = self._marker(session)
            state = session.fetch_one(
                SqlStatement(
                    "SELECT project_id,generation,authority,readiness,active_coverage,migration_id,plan_checksum FROM execution_state WHERE singleton=1"
                )
            )
            if marker is None or marker["state"] != "ready":
                return False
            if (
                marker["plan_checksum"] != plan["plan_checksum"]
                or state is None
                or state.values
                != (
                    plan["project_id"],
                    1,
                    "sql",
                    "ready",
                    "complete",
                    MIGRATION_ID,
                    plan["plan_checksum"],
                )
            ):
                raise MaintenanceError("execution_state_conflict")
        # Backup remains required evidence even after committed cutover.
        journal = self._backup(plan, evidence)
        self._check_marker(
            marker, plan, evidence, project, journal["backup_manifest_checksum"]
        )
        self._verification_snapshot(evidence, create=False)
        return True

    @staticmethod
    def _publish(
        operation: str, plan: Mapping[str, object], evidence: Path, project: Path
    ) -> JsonObject:
        report = {
            "schema_version": 1,
            "operation": operation,
            "status": "ready",
            "blocked": False,
            "migration_id": MIGRATION_ID,
            "plan_checksum": plan["plan_checksum"],
            "phase": "ready",
            "checkpoint": cast(Mapping[str, int], plan["counts"])["import_units"],
            "authority": "sql",
            "active_coverage": "complete",
            "history_complete": False,
            "counts": plan["counts"],
            "error": None,
            "evidence": [evidence.relative_to(project).as_posix()],
        }
        # Report is derived. Failure does not reverse the sole SQL commit.
        try:
            _atomic(evidence / "report.json", report)
        except OSError:
            report["publication_pending"] = True
        return report

    @staticmethod
    def _failure(operation: str, code: str) -> JsonObject:
        return {
            "schema_version": 1,
            "operation": operation,
            "status": "failed",
            "blocked": True,
            "migration_id": MIGRATION_ID,
            "plan_checksum": None,
            "phase": "blocked",
            "checkpoint": None,
            "authority": "unknown",
            "active_coverage": "unknown",
            "history_complete": False,
            "counts": {},
            "error": {"code": code},
            "evidence": [],
        }
