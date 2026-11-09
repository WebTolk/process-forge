"""Bounded private delivery of an immutable execution context to one attempt."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

from ..work.context import (
    fingerprint,
    portable_path,
    scope_allows,
    stage_view,
    validate_execution_contract,
)

MAX_BYTES = 4 * 1024 * 1024
INLINE_FILE_BYTES = 64 * 1024
INLINE_TOTAL_BYTES = 256 * 1024
OUTPUT_FILE_BYTES = 8 * 1024 * 1024
OUTPUT_TOTAL_BYTES = 32 * 1024 * 1024


def digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def bounded_read(path: Path, maximum: int = MAX_BYTES) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise ValueError("prepared_file_invalid_or_oversized")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError("prepared_file_invalid_or_oversized")
    return raw


def _resolved_path(path: Path) -> Path:
    if os.name == "nt":
        try:
            info = path.lstat()
        except FileNotFoundError:
            info = None
        # Resolving an ordinary file while it is deleted can expose NTFS's
        # $Deleted handle name. Its location is the resolved parent plus name;
        # directories, links and other reparse points still resolve fully.
        ordinary = info is None or (
            stat.S_ISREG(info.st_mode)
            and not info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
        )
        resolved = path.parent.resolve() / path.name if ordinary else path.resolve()
        # A file removed during Windows realpath's prefix verification can
        # retain an equivalent extended path. Normalize known drive/UNC forms
        # before containment checks; do not reinterpret other device namespaces.
        value = str(resolved)
        if value.startswith("\\\\?\\UNC\\"):
            return Path("\\\\" + value[8:])
        if (
            value.startswith("\\\\?\\")
            and len(resolved.drive) == 6
            and resolved.drive.endswith(":")
        ):
            return Path(value[4:])
        return resolved
    return path.resolve()


def local_file(project: Path, relative: str) -> Path:
    path = project / portable_path(relative)
    if (
        not _resolved_path(path).is_relative_to(_resolved_path(project))
        or path.is_symlink()
    ):
        raise ValueError("prepared_path_outside_project")
    current = _resolved_path(project)
    for part in path.relative_to(project).parts:
        current /= part
        if current.is_symlink() or _resolved_path(current) != current.absolute():
            raise ValueError("prepared_path_redirected")
    return path


def private_file(project: Path, relative: str) -> Path:
    path = local_file(project, relative)
    # A lexical runtime prefix is insufficient: even an in-project junction
    # can redirect private delivery bytes into public product/artifact files.
    path.relative_to(_resolved_path(project) / ".pf" / "runtime" / "agent-runs")
    return path


def output_records(
    project: Path, outputs: dict[str, Any], *, required: bool = False
) -> list[dict[str, Any]]:
    specs = {
        item["path"]: bool(item.get("required", True))
        for item in outputs["required_outputs"]
        if item.get("path")
    }
    report = outputs.get("expected_report", {}).get("artifact")
    if report:
        specs[report] = True
    result, total = [], 0
    for relative, mandatory in sorted(specs.items()):
        path = local_file(project, relative)
        item: dict[str, Any] = {
            "path": relative,
            "required": mandatory,
            "status": "missing",
        }
        if path.exists():
            raw = bounded_read(path, OUTPUT_FILE_BYTES)
            total += len(raw)
            if total > OUTPUT_TOTAL_BYTES:
                raise ValueError("prepared_output_budget_exceeded")
            item.update(
                status="present",
                checksum=digest(raw),
                size=len(raw),
                mtime_ns=path.stat().st_mtime_ns,
            )
        elif required and mandatory:
            raise ValueError("prepared_output_missing:" + relative)
        result.append(item)
    return result


def semantic_input(project: Path, task: dict, capsule: dict, core: Any) -> dict:
    from processforge_core.work.paths import WorkPaths

    from .resources import authorize_resources

    assignment = WorkPaths().assignment_document(project, task["id"])
    run = core.load_run(project, task["run_id"])
    if "process_execution" in run:
        pin = task.get("process_execution") or {}
        if not pin.get("assignment_capsule_checksum") or pin.get(
            "assignment_capsule"
        ) != core.rel(core.assignment_capsule_path(project, task["id"]), project):
            raise ValueError("work_context_mismatch")
    validation = validate_execution_contract(
        project, assignment, task, capsule, core, require_ready=True
    )
    if validation["status"] != "valid":
        raise ValueError(validation.get("reason") or "execution_contract_invalid")
    contract = capsule["execution_contract"]
    if contract.get("contract_version") == 2 or contract.get("egress"):
        # Strict v2 must enter the managed broker. Never prepare an unfiltered
        # private prompt for a native executor that has not proved mediation.
        raise ValueError("enforcement_unavailable")
    report = contract["outputs"].get("expected_report", {}).get("artifact")
    if not report:
        raise ValueError("worker_report_undeclared")
    if not any(
        scope_allows(contract["scope"], report, action)
        for action in ("write_artifact", "write_product")
    ):
        raise ValueError("output_scope_denied")
    sources, inline = [], 0
    for original in contract["required_sources"]:
        item = copy.deepcopy(original)
        if item.get("status") == "available":
            if not scope_allows(contract["scope"], item["path"], "read"):
                raise ValueError("source_scope_denied")
            raw = bounded_read(
                local_file(project, item["path"]),
                contract["source_limits"]["file_bytes"],
            )
            if digest(raw) != item["checksum"]:
                raise ValueError("required_source_changed")
            allowed = min(INLINE_FILE_BYTES, INLINE_TOTAL_BYTES - inline)
            excerpt = raw[:allowed]
            try:
                text = excerpt.decode("utf-8")
                if "\x00" in text:
                    raise UnicodeError()
            except UnicodeError:
                text, excerpt = "", b""
            item.update(
                delivery="inline" if len(excerpt) == len(raw) else "reference",
                truncated=len(excerpt) != len(raw),
                inline_bytes=len(excerpt),
            )
            if excerpt:
                item.update(content=text, excerpt_checksum=digest(excerpt))
                inline += len(excerpt)
        sources.append(item)
    capsule_path = core.assignment_capsule_path(project, task["id"])
    return {
        "identity": copy.deepcopy(contract["identity"]),
        "objective": contract["assignment_intent"]["objective"],
        "capsule": {
            "path": core.rel(capsule_path, project),
            "checksum": digest(bounded_read(capsule_path)),
            "contract_checksum": contract["contract_checksum"],
            "intent_checksum": contract["assignment_intent_checksum"],
        },
        "snapshot": copy.deepcopy(contract["snapshot"]),
        "process": copy.deepcopy(contract["process"]),
        "stage": stage_view(capsule, task),
        "scope": copy.deepcopy(contract["scope"]),
        "outputs": copy.deepcopy(contract["outputs"]),
        "sources": sources,
        "capabilities": copy.deepcopy(contract["capabilities"]),
        "parameters": copy.deepcopy(contract["parameters"]),
        "subagent_policy": copy.deepcopy(
            contract["assignment_intent"]["subagent_policy"]
        ),
        "resources": authorize_resources(project, task, capsule, core),
        "worker_may_rebuild_context": False,
    }


def build(project: Path, task: dict, capsule: dict, attempt: int, core: Any) -> dict:
    if type(attempt) is not int or attempt < 1:
        raise ValueError("prepared_attempt_invalid")
    semantic = semantic_input(project, task, capsule, core)
    return {
        "schema_version": 1,
        "kind": "pf.prepared-input",
        "visibility": "private_runtime",
        "project_root": str(project.resolve()),
        "identity": {**semantic["identity"], "attempt": attempt},
        "input": semantic,
        "input_fingerprint": fingerprint(semantic),
        "output_baseline": output_records(project, semantic["outputs"]),
        "limits": {
            "json_bytes": MAX_BYTES,
            "inline_file_bytes": INLINE_FILE_BYTES,
            "inline_total_bytes": INLINE_TOTAL_BYTES,
        },
    }


def encoded(document: dict) -> bytes:
    raw = (
        json.dumps(
            document, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False
        )
        + "\n"
    ).encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise ValueError("prepared_input_budget_exceeded")
    return raw


def write_once(path: Path, document: dict) -> str:
    raw = encoded(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic, no-clobber publication: an interrupted write leaves no partial
    # final manifest/receipt. Hard-link creation fails if the target exists.
    temporary = None
    owned: tuple[int, int] | None = None
    primary: BaseException | None = None
    publication = "not_linked"
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".prepared-", suffix=".tmp", dir=path.parent, delete=os.name == "nt"
        ) as stream:
            try:
                temporary = Path(stream.name)
                info = os.fstat(stream.fileno())
                owned = (info.st_dev, info.st_ino)
                written = stream.write(raw)
                if type(written) is not int or written != len(raw):
                    raise OSError("prepared_incomplete_write")
                stream.flush()
                os.fsync(stream.fileno())
                if os.name == "nt":
                    # Keep the sole delete-on-close descriptor through readback
                    # and no-clobber link; reopening it changes Windows lifetime.
                    stream.seek(0)
                    if stream.read() != raw:
                        raise OSError("prepared_incomplete_write")
                    current = temporary.lstat()
                    opened = os.fstat(stream.fileno())
                    if (
                        (current.st_dev, current.st_ino) != owned
                        or (opened.st_dev, opened.st_ino) != owned
                        or not stat.S_ISREG(current.st_mode)
                        or getattr(current, "st_file_attributes", 0)
                        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
                    ):
                        raise OSError("temporary_changed")
                    os.link(temporary, path)
                    publication = "linked"
            except BaseException as exc:
                primary = exc
                raise
        if os.name != "nt":
            os.link(temporary, path)
            publication = "linked"
    except BaseException as exc:
        if primary is not None and exc is not primary:
            BaseException.add_note(
                primary,
                f"prepared stream close failed; staging={temporary}; "
                f"publication={publication}; "
                f"cleanup={type(exc).__name__}: {exc}",
            )
            raise primary
        primary = exc
        raise
    finally:
        if temporary is not None and owned is not None:
            try:
                try:
                    current = temporary.lstat()
                except FileNotFoundError:
                    if os.name != "nt":
                        raise
                else:
                    if os.name == "nt":
                        raise OSError("staging_cleanup_pending")
                    if (
                        (current.st_dev, current.st_ino) != owned
                        or not stat.S_ISREG(current.st_mode)
                        or getattr(current, "st_file_attributes", 0)
                        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
                    ):
                        raise OSError("temporary_changed")
                    temporary.unlink()
            except BaseException as cleanup:
                note = (
                    f"prepared staging cleanup failed; staging={temporary}; "
                    f"publication={publication}; "
                    f"cleanup={type(cleanup).__name__}: {cleanup}"
                )
                if primary is not None:
                    BaseException.add_note(primary, note)
                else:
                    BaseException.add_note(cleanup, note)
                    raise
    return digest(raw)


def load(
    project: Path, task: dict, state: dict, core: Any, *, current: bool = True
) -> dict:
    reference = state.get("prepared_input") or {}
    attempt = state.get("attempt")
    if isinstance(attempt, str) and attempt.isdigit():
        attempt = int(attempt)
    if type(attempt) is not int or attempt < 1:
        raise ValueError("prepared_attempt_invalid")
    from processforge_core.work.paths import WorkPaths

    expected = (
        WorkPaths().worker_run(project, task["run_id"], task["id"])["root"]
        / "attempts"
        / str(attempt)
        / "prepared-input.json"
    )
    if reference.get("path") != core.rel(expected, project):
        raise ValueError("prepared_input_reference_mismatch")
    raw = bounded_read(private_file(project, reference["path"]))
    if digest(raw) != reference.get("checksum"):
        raise ValueError("prepared_input_checksum_mismatch")
    doc = json.loads(raw)
    identity = doc.get("identity") or {}
    if (
        doc.get("schema_version") != 1
        or doc.get("kind") != "pf.prepared-input"
        or identity.get("run_id") != task["run_id"]
        or identity.get("assignment_id") != task["id"]
        or identity.get("attempt") != attempt
        or identity.get("project_id") != core.project_id(project)
        or doc.get("project_root") != str(project.resolve())
        or doc.get("input_fingerprint") != fingerprint(doc.get("input"))
    ):
        raise ValueError("prepared_input_identity_mismatch")
    capsule = core.load_yaml_document(core.assignment_capsule_path(project, task["id"]))
    if identity != {
        **capsule.get("execution_contract", {}).get("identity", {}),
        "attempt": attempt,
    }:
        raise ValueError("prepared_input_context_mismatch")
    if current and semantic_input(project, task, capsule, core) != doc["input"]:
        raise ValueError("prepared_input_changed")
    return doc


def collection_receipt(
    project: Path, task: dict, state: dict, core: Any
) -> tuple[Path, dict]:
    doc = load(project, task, state, core)
    receipt_path = private_file(project, state["prepared_input"]["path"]).with_name(
        "collection-receipt.json"
    )
    private_file(project, receipt_path.relative_to(project).as_posix())
    outputs = output_records(project, doc["input"]["outputs"], required=True)
    pinned_outputs = [
        {key: value for key, value in item.items() if key != "mtime_ns"}
        for item in outputs
    ]
    receipt = {
        "schema_version": 1,
        "identity": doc["identity"],
        "prepared_input": state["prepared_input"],
        "outputs": pinned_outputs,
    }
    receipt["receipt_id"] = fingerprint(receipt)
    if receipt_path.exists():
        if json.loads(bounded_read(receipt_path)) != receipt:
            raise ValueError("collected_output_changed")
        return receipt_path, receipt
    baseline = {item["path"]: item for item in doc["output_baseline"]}
    for item in outputs:
        if item["status"] == "present" and item == baseline.get(item["path"]):
            raise ValueError("output_not_attributable_to_attempt:" + item["path"])
    write_once(receipt_path, receipt)
    return receipt_path, receipt


def bind_managed_scratch(project: Path, document: dict) -> None:
    """Attach only a newly produced private ordinary-worker scratch contract."""
    from .command import allocate_scratch

    allocate_scratch(project, document)


def _collection_json(raw: bytes) -> dict[str, Any]:
    """Parse bounded historical metadata without ambiguous JSON values."""
    from math import isfinite

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("accepted_collection_invalid")
            result[key] = value
        return result

    def number(value: str) -> float:
        parsed = float(value)
        if not isfinite(parsed):
            raise ValueError("accepted_collection_invalid")
        return parsed

    def constant(value: str) -> Any:
        raise ValueError("accepted_collection_invalid")

    try:
        value = json.loads(
            raw,
            object_pairs_hook=pairs,
            parse_float=number,
            parse_constant=constant,
        )
    except (UnicodeError, RecursionError) as error:
        raise ValueError("accepted_collection_invalid") from error
    if not isinstance(value, dict):
        raise ValueError("accepted_collection_invalid")
    return value


def _collection_checksum(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(char in "0123456789abcdef" for char in value[7:])
    )


def _collection_outputs(outputs: Any, records: Any) -> None:
    """Check saved producer pins; never resolve or inspect output paths."""
    if not isinstance(outputs, dict) or not isinstance(records, list):
        raise ValueError("accepted_collection_outputs_invalid")
    declared = outputs.get("required_outputs")
    if not isinstance(declared, list):
        raise ValueError("accepted_collection_outputs_invalid")
    specs: dict[str, bool] = {}
    for item in declared:
        if not isinstance(item, dict) or type(item.get("required", True)) is not bool:
            raise ValueError("accepted_collection_outputs_invalid")
        relative = item.get("path")
        if relative:
            if portable_path(relative) != relative:
                raise ValueError("accepted_collection_outputs_invalid")
            specs[relative] = item.get("required", True)
    report = outputs.get("expected_report", {}).get("artifact")
    if not report or portable_path(report) != report:
        raise ValueError("accepted_collection_outputs_invalid")
    specs[report] = True
    if len(records) != len(specs):
        raise ValueError("accepted_collection_outputs_invalid")
    total = 0
    for (relative, required), item in zip(sorted(specs.items()), records):
        if (
            not isinstance(item, dict)
            or item.get("path") != relative
            or type(item.get("required")) is not bool
            or item["required"] != required
        ):
            raise ValueError("accepted_collection_outputs_invalid")
        keys = {"path", "required", "status"}
        if item.get("status") == "present":
            if (
                set(item) != keys | {"checksum", "size"}
                or not _collection_checksum(item["checksum"])
                or type(item["size"]) is not int
                or not 0 <= item["size"] <= OUTPUT_FILE_BYTES
            ):
                raise ValueError("accepted_collection_outputs_invalid")
            total += item["size"]
        elif item.get("status") != "missing" or required or set(item) != keys:
            raise ValueError("accepted_collection_outputs_invalid")
    if total > OUTPUT_TOTAL_BYTES:
        raise ValueError("prepared_output_budget_exceeded")


def verify_accepted_collection(
    project: Path, task: dict, state: dict, core: Any
) -> dict[str, Any]:
    """Read completed acceptance for one trusted exact historical attempt.

    The caller owns current authorization, creation/resource validation, native
    end-of-use, SQL reconciliation and the serialization/CAS of returned pins.
    This proof grants no launch, cleanup or output-acceptance authority.
    """
    from processforge_core.work.paths import WorkPaths

    attempt = state.get("attempt")
    reference = state.get("prepared_input")
    if type(attempt) is not int or attempt < 1:
        raise ValueError("prepared_attempt_invalid")
    if (
        not isinstance(reference, dict)
        or set(reference) != {"path", "checksum"}
        or not isinstance(reference["path"], str)
        or not _collection_checksum(reference["checksum"])
    ):
        raise ValueError("prepared_input_reference_mismatch")
    document = load(project, task, state, core, current=False)
    prepared_path = private_file(project, reference["path"])
    prepared_raw = bounded_read(prepared_path)
    strict_document = _collection_json(prepared_raw)
    if (
        digest(prepared_raw) != reference["checksum"]
        or fingerprint(strict_document) != fingerprint(document)
        or type(strict_document.get("schema_version")) is not int
        or type(strict_document.get("identity", {}).get("attempt")) is not int
    ):
        raise ValueError("prepared_input_identity_mismatch")
    capsule_path = core.assignment_capsule_path(project, task["id"])
    capsule_relative = capsule_path.relative_to(project).as_posix()
    capsule_path = local_file(project, capsule_relative)
    capsule_raw = bounded_read(capsule_path)
    capsule = core.load_yaml_document(capsule_path)
    if bounded_read(capsule_path) != capsule_raw:
        raise ValueError("accepted_collection_changed")
    validation = validate_execution_contract(
        project,
        WorkPaths().assignment_document(project, task["id"]),
        task,
        capsule,
        core,
        check_sources=False,
        require_ready=False,
    )
    if validation["status"] != "valid":
        raise ValueError(validation.get("reason") or "execution_contract_invalid")
    contract = capsule["execution_contract"]
    saved = strict_document["input"]
    expected_capsule = {
        "path": capsule_relative,
        "checksum": digest(capsule_raw),
        "contract_checksum": contract["contract_checksum"],
        "intent_checksum": contract["assignment_intent_checksum"],
    }
    assignment_pin = task.get("process_execution") or {}
    if (
        strict_document["identity"] != {**contract["identity"], "attempt": attempt}
        or assignment_pin.get("assignment_capsule") != capsule_relative
        or assignment_pin.get("assignment_capsule_checksum") != digest(capsule_raw)
        or saved.get("capsule") != expected_capsule
        or any(
            fingerprint(saved.get(key)) != fingerprint(contract[key])
            for key in ("identity", "process", "snapshot", "outputs", "scope")
        )
    ):
        raise ValueError("prepared_input_context_mismatch")
    if bounded_read(capsule_path) != capsule_raw:
        raise ValueError("accepted_collection_changed")
    snapshot: list[dict[str, Any]] = []

    def pin(path: Path, raw: bytes | None) -> None:
        snapshot.append(
            {"path": path.relative_to(project).as_posix(), "status": "missing"}
            if raw is None
            else {
                "path": path.relative_to(project).as_posix(),
                "status": "present",
                "checksum": digest(raw),
                "size": len(raw),
            }
        )

    pin(prepared_path, prepared_raw)
    pin(capsule_path, capsule_raw)
    paths = [
        private_file(
            project, prepared_path.with_name(name).relative_to(project).as_posix()
        )
        for name in ("collection-receipt.json", "collection-complete.json")
    ]
    raws: list[bytes | None] = []
    for path in paths:
        try:
            path.lstat()
        except FileNotFoundError:
            raw = None
        else:
            raw = bounded_read(path)
        raws.append(raw)
        pin(path, raw)
    receipt_raw, completion_raw = raws
    if receipt_raw is None:
        if completion_raw is not None:
            raise ValueError("accepted_collection_receipt_missing")
        return {"status": "not_accepted", "snapshot": snapshot}
    receipt = _collection_json(receipt_raw)
    if (
        set(receipt)
        != {"schema_version", "identity", "prepared_input", "outputs", "receipt_id"}
        or type(receipt["schema_version"]) is not int
        or receipt["schema_version"] != 1
        or fingerprint(receipt["identity"]) != fingerprint(strict_document["identity"])
        or receipt["prepared_input"] != reference
        or not _collection_checksum(receipt["receipt_id"])
        or receipt["receipt_id"]
        != fingerprint({k: v for k, v in receipt.items() if k != "receipt_id"})
    ):
        raise ValueError("accepted_collection_receipt_invalid")
    _collection_outputs(saved["outputs"], receipt["outputs"])
    if completion_raw is None:
        return {"status": "not_accepted", "snapshot": snapshot}
    completion = _collection_json(completion_raw)
    if (
        set(completion) != {"schema_version", "receipt_id"}
        or type(completion["schema_version"]) is not int
        or completion["schema_version"] != 1
        or completion["receipt_id"] != receipt["receipt_id"]
    ):
        raise ValueError("accepted_collection_completion_invalid")
    return {
        "status": "accepted",
        "identity": copy.deepcopy(strict_document["identity"]),
        "receipt": receipt,
        "completion": completion,
        "snapshot": snapshot,
    }
