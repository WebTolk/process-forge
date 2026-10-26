"""Private ordinary worker scratch: explicit scope, creation and exact-attempt use.

This contract adds no resource group, native maintenance authority or public flag.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..configuration.models import TemporaryFilesConfig
from ..maintenance.temporary_disposal import (
    _CREATED,
    CleanupReceipt,
    OwnedTemporary,
    TemporaryUse,
    _parent,
    create_owned_directory,
    dispose_owned,
    release_owned,
)
from ..work.context import managed_scratch_namespace
from .input import bounded_read, digest, local_file, private_file, write_once

RECORD_LIMIT = 65536
MARKER_KEYS = {
    "schema_version",
    "kind",
    "identity",
    "owner_id",
    "resource_id",
    "path",
    "object_identity",
    "record",
    "use",
}
RECORD_KEYS = {
    "schema_version",
    "kind",
    "identity",
    "owner_id",
    "resource_id",
    "path",
    "object_identity",
    "boundary",
    "use",
}


_PREPARATION: ContextVar[list[tuple[OwnedTemporary, dict[str, Any]]] | None] = (
    ContextVar("worker_scratch_preparation", default=None)
)


@contextmanager
def preparation_scratch():
    """Finalize aborted, unpublished allocations after outer locks unwind."""
    pending: list[tuple[OwnedTemporary, dict[str, Any]]] = []
    token = _PREPARATION.set(pending)
    primary: BaseException | None = None
    try:
        yield
    except BaseException as error:
        primary = error
        raise
    finally:
        _PREPARATION.reset(token)
        for resource, document in pending:
            # Only the actual in-memory producer can register this callback.
            # Durable authoritative binding disarms it before outer locks unwind.
            path = _attempt(Path(document["project_root"]), document["identity"])
            try:
                failure = path.with_name("scratch-preparation-failure.json")
                payload = {
                    "schema_version": 1,
                    "identity": document["identity"],
                    "resource_id": resource.resource_id,
                    "reason": type(primary).__name__
                    if primary
                    else "preparation_unpublished",
                }
                write_once(failure, payload)
                receipt = dispose_owned(release_owned(resource))
                from ..maintenance.temporary_disposal import atomic_staging

                with atomic_staging(
                    path.with_name("scratch-cleanup.json")
                ) as temporary:
                    temporary.write_text(
                        json.dumps(
                            {
                                "schema_version": 1,
                                "identity": document["identity"],
                                **asdict(receipt),
                            }
                        )
                        + "\n",
                        encoding="utf8",
                    )
                    temporary.replace(path.with_name("scratch-cleanup.json"))
                if receipt.result not in {"deleted", "already_absent"}:
                    raise OSError("temporary_cleanup:" + receipt.result)
            except (OSError, ValueError) as error:
                if primary is not None:
                    primary.add_note(
                        "scratch_preparation_cleanup:" + type(error).__name__
                    )
                else:
                    raise


def scratch_published(document: dict[str, Any]) -> None:
    """Transfer lifetime only after durable authoritative attempt binding."""
    pending = _PREPARATION.get()
    if pending is not None:
        pending[:] = [
            (resource, doc) for resource, doc in pending if doc is not document
        ]


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ValueError("scratch_record_invalid")
        result[key] = value
    return result


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(bounded_read(path, RECORD_LIMIT), object_pairs_hook=_pairs)
    if not isinstance(value, dict):
        raise ValueError("scratch_record_invalid")
    return value


def _attempt(project: Path, identity: dict[str, Any]) -> Path:
    from ..work.paths import WorkPaths

    if (
        type(identity.get("attempt")) is not int
        or identity["attempt"] < 1
        or any(
            not isinstance(identity.get(k), str)
            or not identity[k]
            or "/" in identity[k]
            or "\\" in identity[k]
            or identity[k] in {".", ".."}
            for k in ("project_id", "run_id", "assignment_id", "context_id")
        )
    ):
        raise ValueError("scratch_identity_invalid")
    path = WorkPaths().worker_run(
        project, identity["run_id"], identity["assignment_id"]
    )["root"]
    path = path / "attempts" / str(identity["attempt"]) / "scratch-resource.json"
    return private_file(project, path.relative_to(project).as_posix())


def validate_resource_record(record: dict[str, Any], document: dict[str, Any]) -> None:
    """Validate bounded metadata; this function alone never proves ownership."""
    marker = document.get("managed_scratch")
    scope = document["input"]["scope"]
    if (
        not isinstance(marker, dict)
        or set(marker) != MARKER_KEYS
        or not isinstance(record, dict)
        or set(record) != RECORD_KEYS
        or type(marker["schema_version"]) is not int
        or type(record["schema_version"]) is not int
        or marker["schema_version"] != 1
        or record["schema_version"] != 1
        or marker["kind"] != "pf.worker-scratch"
        or record["kind"] != "directory"
        or marker["identity"] != document["identity"]
        or record["identity"] != document["identity"]
        or marker["use"] != "disposable_worker_temp"
        or not isinstance(record["use"], dict)
        or type(record["use"].get("released")) is not bool
        or type(record["use"].get("consumers")) is not int
        or type(record["use"].get("evidence_finalized")) is not bool
        or record["use"]
        != {"released": False, "consumers": 1, "evidence_finalized": False}
        or marker["owner_id"] != scope.get("ownership", {}).get("owner_id")
        or record["owner_id"] != marker["owner_id"]
    ):
        raise ValueError("scratch_record_invalid")
    namespace = managed_scratch_namespace(scope)
    resource_id = marker["resource_id"]
    if (
        not namespace
        or not isinstance(resource_id, str)
        or len(resource_id) != 32
        or any(c not in "0123456789abcdef" for c in resource_id)
        or marker["path"] != namespace + "/pf-scratch-" + resource_id
        or record["boundary"] != namespace
        or any(
            record[k] != marker[k] for k in ("path", "resource_id", "object_identity")
        )
        or not isinstance(marker["object_identity"], list)
        or len(marker["object_identity"]) != 2
        or any(type(x) is not int or x < 0 for x in marker["object_identity"])
    ):
        raise ValueError("scratch_scope_denied")
    root = marker["path"] + "/"
    protected = [x.get("path", "") for x in document["input"].get("sources", [])]
    protected += [
        x.get("path", "")
        for x in document["input"]["outputs"].get("required_outputs", [])
        if isinstance(x, dict)
    ]
    protected.append(
        document["input"]["outputs"].get("expected_report", {}).get("artifact", "")
    )
    if any(
        path == marker["path"] or path.startswith(root) for path in protected if path
    ):
        raise ValueError("scratch_needed_input_or_output")


def allocate_scratch(project: Path, document: dict[str, Any]) -> None:
    """Core creates one namespace only under an actual immutable write grant."""
    namespace = managed_scratch_namespace(document["input"].get("scope", {}))
    if namespace is None:
        return
    project = project.absolute()
    boundary = local_file(project, namespace)
    # Create only the explicitly granted literal namespace, pinning all ancestors.
    # Missing intermediate parents require a broader explicit producer contract.
    if not boundary.exists():
        with _parent(boundary) as parent:
            os.mkdir(
                boundary if parent is None else boundary.name,
                mode=0o777 if os.name == "nt" else 0o700,
                dir_fd=parent,
            )
    resource = create_owned_directory(boundary)
    pending = _PREPARATION.get()
    if pending is not None:
        pending.append((resource, document))
    identity = document["identity"]
    record_path = _attempt(project, identity)
    owner = document["input"]["scope"]["ownership"]["owner_id"]
    record = {
        "schema_version": 1,
        "kind": "directory",
        "identity": identity,
        "owner_id": owner,
        "resource_id": resource.resource_id,
        "path": resource.path.relative_to(project).as_posix(),
        "boundary": namespace,
        "object_identity": list(resource.identity),
        "use": {"released": False, "consumers": 1, "evidence_finalized": False},
    }
    checksum = write_once(record_path, record)
    document["managed_scratch"] = {
        **{
            k: record[k]
            for k in (
                "schema_version",
                "identity",
                "owner_id",
                "resource_id",
                "path",
                "object_identity",
            )
        },
        "kind": "pf.worker-scratch",
        "use": "disposable_worker_temp",
        "record": {
            "path": record_path.relative_to(project).as_posix(),
            "sha256": checksum,
            "size": record_path.stat().st_size,
        },
    }


def read_attempt_resources(
    project: Path, document: dict[str, Any]
) -> OwnedTemporary | None:
    """Read only the selected creation record sealed by the immutable input."""
    marker = document.get("managed_scratch")
    if marker is None:
        return None
    if not isinstance(marker, dict) or set(marker) != MARKER_KEYS:
        raise ValueError("scratch_record_invalid")
    path = _attempt(project, document["identity"])
    reference = marker["record"]
    if (
        not isinstance(reference, dict)
        or set(reference) != {"path", "sha256", "size"}
        or reference["path"] != path.relative_to(project).as_posix()
        or type(reference["size"]) is not int
        or not 1 <= reference["size"] <= RECORD_LIMIT
    ):
        raise ValueError("scratch_record_invalid")
    raw = bounded_read(path, RECORD_LIMIT)
    if len(raw) != reference["size"] or digest(raw) != reference["sha256"]:
        raise ValueError("scratch_record_changed")
    record = json.loads(raw, object_pairs_hook=_pairs)
    validate_resource_record(record, document)
    target = local_file(project, record["path"])
    return OwnedTemporary(
        record["resource_id"],
        target,
        (record["object_identity"][0], record["object_identity"][1]),
        local_file(project, record["boundary"]),
        TemporaryUse(False, 1, False),
        _CREATED,
        "directory",
    )


def scratch_environment(
    document: dict[str, Any], environment: dict[str, str]
) -> dict[str, str]:
    """Bind actual disposable temp producers; old inputs retain their environment."""
    result = dict(environment)
    resource = read_attempt_resources(Path(document["project_root"]), document)
    if resource is not None:
        info = resource.path.lstat()
        if (info.st_dev, info.st_ino) != resource.identity:
            raise ValueError("scratch_identity_changed")
        # local_file refuses directory redirection before an environment is issued.
        result.update(
            {
                key: str(resource.path)
                for key in ("TEMP", "TMP", "TMPDIR", "PF_WORKER_SCRATCH")
            }
        )
    return result


def release_scratch(
    document: dict[str, Any], *, tree_absent: bool, evidence_finalized: bool
) -> None:
    """Publish end-of-use only after owned children and raw receipts finish."""
    if "managed_scratch" not in document:
        return
    if tree_absent is not True or evidence_finalized is not True:
        raise ValueError("scratch_still_needed")
    project = Path(document["project_root"])
    resource = read_attempt_resources(project, document)
    assert resource is not None
    path = _attempt(project, document["identity"]).with_name("scratch-release.json")
    payload = {
        "schema_version": 1,
        "identity": document["identity"],
        "resource_id": resource.resource_id,
        "tree_absent": True,
        "evidence_finalized": True,
    }
    if path.exists():
        if _read(path) != payload:
            raise ValueError("scratch_release_changed")
    else:
        write_once(path, payload)


def finalize_scratch(
    document: dict[str, Any],
    *,
    tree_absent: bool,
    evidence_finalized: bool,
    config: TemporaryFilesConfig = TemporaryFilesConfig(),
    configuration_errors: tuple[str, ...] = (),
) -> CleanupReceipt | None:
    """Dispose only after lifecycle proof; neither PID absence nor metadata suffices."""
    project = Path(document["project_root"])
    resource = read_attempt_resources(project, document)
    if resource is None:
        return None
    if tree_absent is not True or evidence_finalized is not True:
        return CleanupReceipt(resource.resource_id, "needed")
    release_scratch(document, tree_absent=True, evidence_finalized=True)
    receipt = dispose_owned(
        release_owned(resource),
        config=config,
        configuration_errors=configuration_errors,
    )
    path = _attempt(project, document["identity"]).with_name("scratch-cleanup.json")
    from ..maintenance.temporary_disposal import atomic_staging

    if receipt.result == "already_absent" and path.exists():
        previous = _read(path)
        if (
            previous.get("identity") != document["identity"]
            or previous.get("resource_id") != resource.resource_id
        ):
            raise ValueError("scratch_cleanup_changed")
        if previous.get("result") == "deleted" and previous.get("complete") is True:
            return receipt  # Preserve original truthful deleted counts on replay.
    with atomic_staging(path) as temporary:
        temporary.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "identity": document["identity"],
                    **asdict(receipt),
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf8",
        )
        temporary.replace(path)
    return receipt
