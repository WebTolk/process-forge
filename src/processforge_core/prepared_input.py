"""Bounded private delivery of an immutable execution context to one attempt."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
from pathlib import Path
import tempfile
from typing import Any

from .work_context import fingerprint, portable_path, scope_allows, stage_view, validate_execution_contract

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
        ordinary = info is None or (stat.S_ISREG(info.st_mode) and
                                    not info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
        resolved = path.parent.resolve() / path.name if ordinary else path.resolve()
        # A file removed during Windows realpath's prefix verification can
        # retain an equivalent extended path. Normalize known drive/UNC forms
        # before containment checks; do not reinterpret other device namespaces.
        value = str(resolved)
        if value.startswith("\\\\?\\UNC\\"):
            return Path("\\\\" + value[8:])
        if value.startswith("\\\\?\\") and len(resolved.drive) == 6 and resolved.drive.endswith(":"):
            return Path(value[4:])
        return resolved
    return path.resolve()


def local_file(project: Path, relative: str) -> Path:
    path = project / portable_path(relative)
    if not _resolved_path(path).is_relative_to(_resolved_path(project)) or path.is_symlink():
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


def output_records(project: Path, outputs: dict[str, Any], *, required: bool = False) -> list[dict[str, Any]]:
    specs = {item["path"]: bool(item.get("required", True)) for item in outputs["required_outputs"] if item.get("path")}
    report = outputs.get("expected_report", {}).get("artifact")
    if report:
        specs[report] = True
    result, total = [], 0
    for relative, mandatory in sorted(specs.items()):
        path = local_file(project, relative)
        item: dict[str, Any] = {"path": relative, "required": mandatory, "status": "missing"}
        if path.exists():
            raw = bounded_read(path, OUTPUT_FILE_BYTES)
            total += len(raw)
            if total > OUTPUT_TOTAL_BYTES:
                raise ValueError("prepared_output_budget_exceeded")
            item.update(status="present", checksum=digest(raw), size=len(raw), mtime_ns=path.stat().st_mtime_ns)
        elif required and mandatory:
            raise ValueError("prepared_output_missing:" + relative)
        result.append(item)
    return result


def semantic_input(project: Path, task: dict, capsule: dict, core: Any) -> dict:
    from .prepared_resources import authorize_resources

    assignment = core.assignment_yaml_path(project, task["id"])
    run = core.load_run(project, task["run_id"])
    if "process_execution" in run:
        pin = task.get("process_execution") or {}
        if not pin.get("assignment_capsule_checksum") or pin.get("assignment_capsule") != core.rel(core.assignment_capsule_path(project, task["id"]), project):
            raise ValueError("work_context_mismatch")
    validation = validate_execution_contract(project, assignment, task, capsule, core, require_ready=True)
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
    if not any(scope_allows(contract["scope"], report, action) for action in ("write_artifact", "write_product")):
        raise ValueError("output_scope_denied")
    sources, inline = [], 0
    for original in contract["required_sources"]:
        item = copy.deepcopy(original)
        if item.get("status") == "available":
            if not scope_allows(contract["scope"], item["path"], "read"):
                raise ValueError("source_scope_denied")
            raw = bounded_read(local_file(project, item["path"]), contract["source_limits"]["file_bytes"])
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
            item.update(delivery="inline" if len(excerpt) == len(raw) else "reference",
                        truncated=len(excerpt) != len(raw), inline_bytes=len(excerpt))
            if excerpt:
                item.update(content=text, excerpt_checksum=digest(excerpt))
                inline += len(excerpt)
        sources.append(item)
    capsule_path = core.assignment_capsule_path(project, task["id"])
    return {"identity": copy.deepcopy(contract["identity"]), "objective": contract["assignment_intent"]["objective"],
            "capsule": {"path": core.rel(capsule_path, project), "checksum": digest(bounded_read(capsule_path)),
                        "contract_checksum": contract["contract_checksum"], "intent_checksum": contract["assignment_intent_checksum"]},
            "snapshot": copy.deepcopy(contract["snapshot"]), "process": copy.deepcopy(contract["process"]),
            "stage": stage_view(capsule, task), "scope": copy.deepcopy(contract["scope"]),
            "outputs": copy.deepcopy(contract["outputs"]), "sources": sources,
            "capabilities": copy.deepcopy(contract["capabilities"]), "parameters": copy.deepcopy(contract["parameters"]),
            "subagent_policy": copy.deepcopy(contract["assignment_intent"]["subagent_policy"]),
            "resources": authorize_resources(project, task, capsule, core),
            "worker_may_rebuild_context": False}


def build(project: Path, task: dict, capsule: dict, attempt: int, core: Any) -> dict:
    if type(attempt) is not int or attempt < 1:
        raise ValueError("prepared_attempt_invalid")
    semantic = semantic_input(project, task, capsule, core)
    return {"schema_version": 1, "kind": "pf.prepared-input", "visibility": "private_runtime",
            "project_root": str(project.resolve()), "identity": {**semantic["identity"], "attempt": attempt},
            "input": semantic, "input_fingerprint": fingerprint(semantic),
            "output_baseline": output_records(project, semantic["outputs"]),
            "limits": {"json_bytes": MAX_BYTES, "inline_file_bytes": INLINE_FILE_BYTES, "inline_total_bytes": INLINE_TOTAL_BYTES}}


def encoded(document: dict) -> bytes:
    raw = (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise ValueError("prepared_input_budget_exceeded")
    return raw


def write_once(path: Path, document: dict) -> str:
    raw = encoded(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic, no-clobber publication: an interrupted write leaves no partial
    # final manifest/receipt. Hard-link creation fails if the target exists.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".prepared-", suffix=".tmp", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return digest(raw)


def load(project: Path, task: dict, state: dict, core: Any, *, current: bool = True) -> dict:
    reference = state.get("prepared_input") or {}
    attempt = state.get("attempt")
    if isinstance(attempt, str) and attempt.isdigit():
        attempt = int(attempt)
    if type(attempt) is not int or attempt < 1:
        raise ValueError("prepared_attempt_invalid")
    expected = core.worker_run_paths(project, task["run_id"], task["id"])["root"] / "attempts" / str(attempt) / "prepared-input.json"
    if reference.get("path") != core.rel(expected, project):
        raise ValueError("prepared_input_reference_mismatch")
    raw = bounded_read(private_file(project, reference["path"]))
    if digest(raw) != reference.get("checksum"):
        raise ValueError("prepared_input_checksum_mismatch")
    doc = json.loads(raw)
    identity = doc.get("identity") or {}
    if (doc.get("schema_version") != 1 or doc.get("kind") != "pf.prepared-input"
            or identity.get("run_id") != task["run_id"] or identity.get("assignment_id") != task["id"]
            or identity.get("attempt") != attempt or identity.get("project_id") != core.project_id(project)
            or doc.get("project_root") != str(project.resolve())
            or doc.get("input_fingerprint") != fingerprint(doc.get("input"))):
        raise ValueError("prepared_input_identity_mismatch")
    capsule = core.load_yaml_document(core.assignment_capsule_path(project, task["id"]))
    if identity != {**capsule.get("execution_contract", {}).get("identity", {}), "attempt": attempt}:
        raise ValueError("prepared_input_context_mismatch")
    if current and semantic_input(project, task, capsule, core) != doc["input"]:
        raise ValueError("prepared_input_changed")
    return doc


def collection_receipt(project: Path, task: dict, state: dict, core: Any) -> tuple[Path, dict]:
    doc = load(project, task, state, core)
    receipt_path = private_file(project, state["prepared_input"]["path"]).with_name("collection-receipt.json")
    private_file(project, receipt_path.relative_to(project).as_posix())
    outputs = output_records(project, doc["input"]["outputs"], required=True)
    pinned_outputs = [{key: value for key, value in item.items() if key != "mtime_ns"} for item in outputs]
    receipt = {"schema_version": 1, "identity": doc["identity"], "prepared_input": state["prepared_input"], "outputs": pinned_outputs}
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
