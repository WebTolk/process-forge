"""Fixed native maintenance preparation, validation and finite execution.

Management runtime and source are independently trusted deployment inputs.
Integrity pins do not qualify a platform or confer target access.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import stat
import sys
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from typing import Any

PREPARED_LIMIT = 4 * 1024 * 1024
ARCHIVE_LIMIT = 128 * 1024 * 1024
EXPANDED_LIMIT = 256 * 1024 * 1024
FILE_LIMIT = 32 * 1024 * 1024
MANIFEST_LIMIT = 1024 * 1024
ENTRY_LIMIT = 4096
ROLES = frozenset(
    {
        "harness",
        "descriptor",
        "archive",
        "manifest",
        "controller",
        "native",
        "wrapper",
        "management",
    }
)
IDENTITY_KEYS = frozenset(
    {"project_id", "run_id", "assignment_id", "context_id", "attempt", "kind"}
)


class Rejected(ValueError):
    """A bounded private rejection; never include private paths or input text."""


def reject_unless(condition: bool, code: str) -> None:
    if not condition:
        raise Rejected(code)


def digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def canonical(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
        + b"\n"
    )


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        reject_unless(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def _constant(_: str) -> Any:
    raise Rejected("nonfinite_json")


def document(raw: bytes, limit: int) -> dict[str, Any]:
    reject_unless(0 < len(raw) <= limit, "document_size")
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    except UnicodeError, json.JSONDecodeError, RecursionError:
        raise Rejected("invalid_json") from None
    reject_unless(isinstance(value, dict), "document_shape")
    return dict(value)


def relative(value: Any) -> str:
    reject_unless(isinstance(value, str) and bool(value), "relative_path_required")
    reject_unless(
        "\\" not in value and ":" not in value and "\x00" not in value,
        "unsafe_path",
    )
    parts = value.split("/")
    reject_unless(
        not PurePosixPath(value).is_absolute()
        and all(part not in {"", ".", ".."} for part in parts)
        and all(not part.endswith((".", " ")) for part in parts)
        and all(
            re.fullmatch(r"(?i:con|prn|aux|nul|com[0-9]|lpt[0-9])", part.split(".")[0])
            is None
            for part in parts
        ),
        "unsafe_path",
    )
    return str(value)


def _plain(path: Path, *, file: bool) -> os.stat_result:
    info = path.lstat()
    reject_unless(
        not stat.S_ISLNK(info.st_mode)
        and not (getattr(info, "st_file_attributes", 0) & 0x400)
        and (
            stat.S_ISREG(info.st_mode) and info.st_nlink == 1
            if file
            else stat.S_ISDIR(info.st_mode)
        ),
        "redirected_path",
    )
    return info


def located(root: Path, name: str, *, exists: bool = True) -> Path:
    reject_unless(root.is_absolute(), "root_absolute_required")
    path = root / relative(name)
    for ancestor in reversed(root.parents):
        _plain(ancestor, file=False)
    _plain(root, file=False)
    current = root
    for part in Path(name).parts[:-1]:
        current /= part
        _plain(current, file=False)
    if exists:
        _plain(path, file=True)
    return path


def read_file(path: Path, limit: int) -> bytes:
    before = _plain(path, file=True)
    reject_unless(before.st_size <= limit, "resource_size")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        reject_unless(
            (opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino),
            "resource_replaced",
        )
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    reject_unless(
        len(raw) <= limit
        and (opened.st_size, opened.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
        and len(raw) == after.st_size,
        "resource_changed",
    )
    return raw


def pin(value: Any) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None
    )


def identity(value: Any) -> dict[str, Any]:
    reject_unless(isinstance(value, dict) and set(value) == IDENTITY_KEYS, "identity")
    reject_unless(
        value["kind"] == "work"
        and type(value["attempt"]) is int
        and value["attempt"] > 0
        and all(
            isinstance(value[key], str)
            and re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", value[key]) is not None
            for key in IDENTITY_KEYS - {"attempt", "kind"}
        ),
        "identity",
    )
    return dict(value)


def _body_granted(prepared: dict[str, Any], row: dict[str, Any]) -> bool:
    import fnmatch

    scope = prepared["input"].get("scope", {})
    if (
        "read" not in scope.get("allowed_actions", [])
        or "read" in scope.get("forbidden_actions", [])
        or row["path"] not in scope.get("allowed_read_files", [])
        or any(
            fnmatch.fnmatchcase(row["path"].casefold(), pattern.casefold())
            for pattern in scope.get("forbidden_files", [])
        )
    ):
        return False
    sources = prepared["input"].get("sources", [])
    return isinstance(sources, list) and any(
        isinstance(source, dict)
        and source.get("path") == row["path"]
        and source.get("checksum") == row["sha256"]
        and source.get("size") == row["size"]
        and source.get("delivery") in {"inline", "reference"}
        and source.get("status") == "available"
        for source in sources
    )


def qualify_archive(archive: bytes, manifest: bytes) -> dict[str, Any]:
    """Check exact frozen archive membership and bytes without extraction/import."""
    expected = document(manifest, MANIFEST_LIMIT)
    reject_unless(
        set(expected) == {"schema_version", "files"}
        and type(expected["schema_version"]) is int
        and expected["schema_version"] == 1
        and isinstance(expected["files"], list)
        and 0 < len(expected["files"]) <= ENTRY_LIMIT,
        "manifest_shape",
    )
    files: dict[str, dict[str, Any]] = {}
    folded: set[str] = set()
    for row in expected["files"]:
        reject_unless(
            isinstance(row, dict) and set(row) == {"path", "sha256", "size"},
            "manifest_file",
        )
        name = relative(row["path"])
        reject_unless(
            name.casefold() not in folded
            and pin(row["sha256"])
            and type(row["size"]) is int
            and 0 <= row["size"] <= FILE_LIMIT,
            "manifest_file",
        )
        folded.add(name.casefold())
        files[name] = row
    reject_unless(len(archive) <= ARCHIVE_LIMIT, "archive_size")
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as package:
            entries = package.infolist()
            reject_unless(len(entries) == len(files), "archive_membership")
            names: set[str] = set()
            expanded = 0
            for entry in entries:
                name = relative(entry.filename)
                mode = entry.external_attr >> 16
                reject_unless(
                    name not in names
                    and name in files
                    and not entry.is_dir()
                    and not stat.S_ISLNK(mode)
                    and stat.S_IFMT(mode) in {0, stat.S_IFREG}
                    and entry.flag_bits & 1 == 0
                    and entry.compress_type
                    in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED},
                    "archive_member",
                )
                names.add(name)
                row = files[name]
                expanded += entry.file_size
                reject_unless(
                    entry.file_size == row["size"] and expanded <= EXPANDED_LIMIT,
                    "archive_expansion",
                )
                with package.open(entry) as member:
                    raw = member.read(row["size"] + 1)
                reject_unless(
                    len(raw) == row["size"] and digest(raw) == row["sha256"],
                    "archive_digest",
                )
    except zipfile.BadZipFile, zlib.error, NotImplementedError, RuntimeError, EOFError:
        raise Rejected("archive_invalid") from None
    return {
        "files": len(files),
        "expanded_bytes": sum(row["size"] for row in files.values()),
    }


def _native_authority(
    semantic: dict[str, Any], selected: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """Intersect the fixed private request, authoritative tool policy and Work.

    No file is read and no command is interpreted by this admission check.
    The standalone harness repeats this bounded check without importing Core.
    """
    import fnmatch
    import json

    def require(ok: bool, reason: str = "native_authority_required") -> None:
        if not ok:
            raise ValueError(reason)

    def seal(value: Any) -> str:
        return (
            "sha256:"
            + hashlib.sha256(
                (
                    json.dumps(
                        value,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=True,
                        allow_nan=False,
                    )
                    + "\n"
                ).encode("ascii")
            ).hexdigest()
        )

    def pinned(value: Any) -> bool:
        return (
            isinstance(value, str)
            and re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None
        )

    def shape(value: Any) -> None:
        require(
            isinstance(value, dict)
            and set(value)
            == {
                "schema_version",
                "identity",
                "job_sha256",
                "descriptor_sha256",
                "runtime",
                "execute_sources",
                "operation",
                "management_sha256",
                "qualification_sha256",
                "deployment",
            }
        )
        require(type(value["schema_version"]) is int and value["schema_version"] == 1)
        ident = value["identity"]
        require(
            isinstance(ident, dict)
            and set(ident)
            == {
                "kind",
                "project_id",
                "run_id",
                "assignment_id",
                "context_id",
                "attempt",
            }
        )
        require(
            ident["kind"] == "work"
            and type(ident["attempt"]) is int
            and ident["attempt"] > 0
            and all(
                isinstance(ident[key], str)
                and re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", ident[key]) is not None
                for key in set(ident) - {"kind", "attempt"}
            )
        )
        require(
            all(
                pinned(value[key])
                for key in (
                    "job_sha256",
                    "descriptor_sha256",
                    "management_sha256",
                    "qualification_sha256",
                )
            )
        )
        runtime = value["runtime"]
        require(
            isinstance(runtime, dict)
            and set(runtime) == {"resource_id", "access", "sha256", "version"}
        )
        require(
            runtime["resource_id"] == "management-python"
            and runtime["access"] == ["body", "execute"]
            and pinned(runtime["sha256"])
            and isinstance(runtime["version"], str)
            and 0 < len(runtime["version"]) <= 64
        )
        rows = value["execute_sources"]
        require(isinstance(rows, list) and len(rows) == 4)
        roles = set()
        for row in rows:
            require(
                isinstance(row, dict) and set(row) == {"role", "path", "sha256", "size"}
            )
            require(
                isinstance(row["role"], str)
                and row["role"] in {"wrapper", "harness", "controller", "native"}
                and row["role"] not in roles
                and isinstance(row["path"], str)
                and pinned(row["sha256"])
                and type(row["size"]) is int
                and 0 < row["size"] <= 32 * 1024 * 1024
            )
            roles.add(row["role"])
        operation = value["operation"]
        require(
            isinstance(operation, str)
            and operation
            in {
                "qualify-archive",
                "construct-management",
                "cold-stage",
                "cold-resume",
                "cold-finalize",
                "cold-release",
            }
        )
        deployment = value["deployment"]
        if operation in {"qualify-archive", "construct-management"}:
            require(deployment is None)
        else:
            require(
                isinstance(deployment, dict)
                and set(deployment)
                == {"access", "operations", "spec_sha256", "management_sha256"}
            )
            require(
                deployment["access"] == ["read", "write", "acl"]
                and deployment["operations"] == [operation]
                and pinned(deployment["spec_sha256"])
                and deployment["management_sha256"] == value["management_sha256"]
            )

    resources = semantic.get("resources", {})
    requests = resources.get("requested", {}).get("tools", [])
    grants = resources.get("grants", {}).get("tools", [])
    job = semantic.get("parameters", {}).get("native_maintenance_job")
    native_requests = [
        r for r in requests if isinstance(r, dict) and "native_maintenance" in r
    ]
    if job is None:
        require(not native_requests)
        return None
    require(
        isinstance(job, dict)
        and set(job)
        == {"schema_version", "identity", "operation", "resources", "runtime", "report"}
    )
    require(type(job["schema_version"]) is int and job["schema_version"] == 1)
    require(len(native_requests) == 1)
    request = native_requests[0]
    require(
        set(request) == {"id", "path_ref", "native_maintenance"}
        and isinstance(request["id"], str)
        and re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", request["id"]) is not None
    )
    require(request["path_ref"] == {"registry": "tools", "id": request["id"]})
    require(
        sum(
            (
                r == request["id"]
                or isinstance(r, dict)
                and (
                    r.get("id") == request["id"]
                    or r.get("path_ref") == request["path_ref"]
                )
            )
            for r in requests
        )
        == 1
    )
    matches = [
        g
        for g in grants
        if isinstance(g, dict)
        and (g.get("id") == request["id"] or g.get("path_ref") == request["path_ref"])
    ]
    require(len(matches) == 1)
    grant = matches[0]
    require(
        set(grant) == {"id", "path_ref", "resolution"}
        and grant["id"] == request["id"]
        and grant["path_ref"] == request["path_ref"]
    )
    resolution = grant["resolution"]
    require(
        isinstance(resolution, dict)
        and set(resolution) == {"status", "entry"}
        and resolution["status"] == "descriptor"
    )
    entry = resolution["entry"]
    require(
        isinstance(entry, dict)
        and entry.get("id") == request["id"]
        and "path" not in entry
        and entry.get("status") == "configured"
        and entry.get("capability") == "processforge.native-maintenance.fixed-v1"
        and isinstance(entry.get("command"), str)
        and bool(entry["command"].strip())
    )
    policy = entry.get("native_maintenance")
    require(
        isinstance(policy, dict)
        and set(policy) == {"schema_version", "profile", "bindings"}
    )
    require(
        type(policy["schema_version"]) is int
        and policy["schema_version"] == 1
        and policy["profile"] == "native-maintenance-fixed-v1"
    )
    bindings = policy["bindings"]
    require(isinstance(bindings, list) and 0 < len(bindings) <= 64)
    for binding in bindings:
        shape(binding)
    require(len({seal(binding) for binding in bindings}) == len(bindings))
    binding = request["native_maintenance"]
    shape(binding)
    require(sum(binding == item for item in bindings) == 1)
    require(
        {key: value for key, value in binding["identity"].items() if key != "attempt"}
        == semantic.get("identity"),
        "native_identity_mismatch",
    )
    require(
        selected is None or selected == binding["identity"], "native_identity_mismatch"
    )
    require(
        job["identity"] == binding["identity"]
        and seal(job) == binding["job_sha256"]
        and job["runtime"] == binding["runtime"]
        and job["operation"] == binding["operation"],
        "native_job_mismatch",
    )
    scope = semantic.get("scope", {})

    def permitted(name: str, action: str, field: str) -> bool:
        return (
            action in scope.get("allowed_actions", [])
            and action not in scope.get("forbidden_actions", [])
            and name in scope.get(field, [])
            and not any(
                fnmatch.fnmatchcase(name.casefold(), pattern.casefold())
                for pattern in scope.get("forbidden_files", [])
            )
        )

    require("execute" not in scope.get("forbidden_actions", []), "native_scope_denied")
    require(
        isinstance(job["report"], str)
        and permitted(job["report"], "write_artifact", "allowed_files"),
        "native_scope_denied",
    )
    require(
        job["report"]
        == semantic.get("outputs", {}).get("expected_report", {}).get("artifact"),
        "native_report_mismatch",
    )
    rows = job["resources"]
    roles = {
        "wrapper",
        "harness",
        "controller",
        "native",
        "descriptor",
        "archive",
        "manifest",
        "management",
    }
    require(isinstance(rows, list) and len(rows) == len(roles))
    by_role = {}
    names = {job["report"].casefold()}
    for row in rows:
        require(
            isinstance(row, dict)
            and set(row) == {"role", "path", "access", "sha256", "size"}
        )
        name = row["path"]
        require(
            isinstance(name, str)
            and bool(name)
            and "\\" not in name
            and ":" not in name
            and "\x00" not in name
            and all(
                part not in {"", ".", ".."} and not part.endswith((".", " "))
                for part in name.split("/")
            )
        )
        require(
            isinstance(row["role"], str)
            and row["role"] in roles
            and row["role"] not in by_role
            and name.casefold() not in names
            and row["access"] == "body"
            and pinned(row["sha256"])
            and type(row["size"]) is int
            and 0 < row["size"] <= 128 * 1024 * 1024
        )
        require(permitted(name, "read", "allowed_read_files"), "native_scope_denied")
        sources = [
            s
            for s in semantic.get("sources", [])
            if isinstance(s, dict) and s.get("path") == name
        ]
        require(
            len(sources) == 1
            and sources[0].get("status") == "available"
            and sources[0].get("checksum") == row["sha256"]
            and sources[0].get("size") == row["size"],
            "native_source_body_required",
        )
        if selected is not None:
            require(
                sources[0].get("delivery") in {"inline", "reference"},
                "native_source_body_required",
            )
        by_role[row["role"]] = row
        names.add(name.casefold())
    require(
        by_role["descriptor"]["sha256"] == binding["descriptor_sha256"]
        and by_role["management"]["sha256"] == binding["management_sha256"],
        "native_source_pin_mismatch",
    )
    require(
        {row["role"]: row for row in binding["execute_sources"]}
        == {
            role: {
                key: value for key, value in by_role[role].items() if key != "access"
            }
            for role in ("wrapper", "harness", "controller", "native")
        },
        "native_execute_source_mismatch",
    )
    return binding


def capture_job(
    prepared: dict[str, Any], root: Path
) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Validate all grants/pins before producing an artifact-only result."""
    selected = identity(prepared.get("identity"))
    _native_authority(prepared.get("input", {}), selected)
    semantic = prepared.get("input")
    if not isinstance(semantic, dict):
        raise Rejected("input_shape")
    reject_unless(
        isinstance(semantic.get("identity"), dict)
        and set(semantic["identity"]) == IDENTITY_KEYS - {"attempt"}
        and {**semantic["identity"], "attempt": selected["attempt"]} == selected,
        "identity_mismatch",
    )
    parameters = semantic.get("parameters")
    if not isinstance(parameters, dict):
        raise Rejected("structured_job_required")
    job = parameters.get("native_maintenance_job")
    if not isinstance(job, dict):
        raise Rejected("structured_job_required")
    reject_unless(
        set(job)
        == {"schema_version", "identity", "operation", "resources", "runtime", "report"}
        and type(job["schema_version"]) is int
        and job["schema_version"] == 1
        and identity(job["identity"]) == selected,
        "job_shape",
    )
    reject_unless(
        job["operation"]
        in {
            "qualify-archive",
            "construct-management",
            "cold-stage",
            "cold-resume",
            "cold-finalize",
            "cold-release",
        },
        "operation_unavailable",
    )
    scope = semantic.get("scope", {})
    report = relative(job["report"])
    reject_unless(
        report.startswith(".pf/artifacts/")
        and "write_artifact" in scope.get("allowed_actions", [])
        and report in scope.get("allowed_files", [])
        and "write_artifact" not in scope.get("forbidden_actions", [])
        and report
        == semantic.get("outputs", {}).get("expected_report", {}).get("artifact"),
        "report_grant_required",
    )
    runtime = job["runtime"]
    reject_unless(
        isinstance(runtime, dict)
        and set(runtime) == {"resource_id", "access", "sha256", "version"}
        and runtime["resource_id"] == "management-python"
        and runtime["access"] == ["body", "execute"]
        and pin(runtime["sha256"])
        and runtime["version"] == sys.version.split()[0],
        "runtime_binding_required",
    )
    # External interpreter body read is permitted only by this explicit native
    # preparation grant, whose resource must be resolved/qualified before spawn.
    reject_unless(
        prepared.get("native_launch", {}).get("maintenance")
        == {"runtime": runtime, "job_sha256": digest(canonical(job))},
        "runtime_body_grant_required",
    )
    reject_unless(
        digest(read_file(Path(sys.executable), FILE_LIMIT)) == runtime["sha256"],
        "runtime_pin_mismatch",
    )
    rows = job["resources"]
    reject_unless(isinstance(rows, list) and len(rows) == len(ROLES), "resource_roles")
    captured: dict[str, bytes] = {}
    resource_pins: dict[str, str] = {}
    paths: set[str] = {report.casefold()}
    for row in rows:
        reject_unless(
            isinstance(row, dict)
            and set(row) == {"role", "path", "access", "sha256", "size"}
            and row["role"] in ROLES
            and row["role"] not in captured
            and row["access"] == "body"
            and pin(row["sha256"])
            and type(row["size"]) is int
            and 0 < row["size"] <= ARCHIVE_LIMIT,
            "resource_grant_invalid",
        )
        name = relative(row["path"])
        reject_unless(name.casefold() not in paths, "resource_alias")
        paths.add(name.casefold())
        reject_unless(
            "read" in scope.get("allowed_actions", [])
            and name in scope.get("allowed_read_files", []),
            "source_scope_required",
        )
        reject_unless(_body_granted(prepared, row), "resource_body_grant_required")
        limit = ARCHIVE_LIMIT if row["role"] == "archive" else MANIFEST_LIMIT
        raw = read_file(located(root, name), limit)
        reject_unless(
            len(raw) == row["size"] and digest(raw) == row["sha256"],
            "resource_pin_mismatch",
        )
        if row["role"] == "harness":
            reject_unless(
                Path(__file__).absolute() == root / name, "harness_path_mismatch"
            )
        captured[row["role"]] = raw
        resource_pins[row["role"]] = row["sha256"]
    return job, captured


def publish(root: Path, name: str, raw: bytes) -> None:
    """Create once; resume can accept identical committed bytes, never overwrite."""
    path = located(root, name, exists=False)
    try:
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        reject_unless(read_file(path, MANIFEST_LIMIT) == raw, "report_conflict")


def main(argv: list[str]) -> int:
    try:
        reject_unless(len(argv) == 1, "fixed_arguments_required")
        source = Path(argv[0]).absolute()
        reject_unless(
            str(source) == os.environ.get("PF_PREPARED_INPUT_FILE"),
            "prepared_pointer_mismatch",
        )
        expected = os.environ.get("PF_PREPARED_INPUT_SHA256")
        reject_unless(pin(expected), "prepared_pin_required")
        raw = read_file(source, PREPARED_LIMIT)
        reject_unless(digest(raw) == expected, "prepared_pin_mismatch")
        prepared = document(raw, PREPARED_LIMIT)
        reject_unless(
            type(prepared.get("schema_version")) is int
            and prepared["schema_version"] == 1
            and prepared.get("kind") == "pf.prepared-input",
            "prepared_shape",
        )
        root = Path(prepared["project_root"])
        reject_unless(
            source == located(root, source.relative_to(root).as_posix()),
            "prepared_path",
        )
        selected = identity(prepared.get("identity"))
        for field, key in (
            ("run_id", "PF_WORKER_RUN_ID"),
            ("assignment_id", "PF_WORKER_TASK_ID"),
            ("attempt", "PF_WORKER_ATTEMPT"),
        ):
            reject_unless(
                str(selected[field]) == os.environ.get(key), "launch_identity"
            )
        reject_unless(
            os.environ.get("PF_PROJECT_ROOT") == str(root)
            and not os.environ.get("PF_AGENT_MODEL")
            and not os.environ.get("PF_AGENT_REASONING_EFFORT"),
            "launch_profile",
        )
        report, result = execute(prepared, root)
        publish(root, report, result)
        sys.stdout.buffer.write(result)
        return 0
    except (
        Rejected,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        RecursionError,
    ):
        # Private exit 125 belongs to this proposal only, not a new PF public code.
        print('{"result":"refused","code":"native_job_invalid"}', file=sys.stderr)
        return 125


def _captured_module(name: str, raw: bytes, filename: str) -> Any:
    """Compile accepted source bytes, never target pyc or import search paths."""
    import types

    module = types.ModuleType(name)
    module.__file__ = filename
    setattr(module, "_captured_source", raw)
    sys.modules[name] = module
    exec(compile(raw, filename, "exec", dont_inherit=True), module.__dict__)
    return module


def _closure(
    prepared: dict[str, Any], root: Path, spec: dict[str, Any]
) -> dict[str, bytes]:
    """Validate the entire explicitly accepted runtime image before any effect."""
    rows = spec["runtime_closure"]
    reject_unless(isinstance(rows, list) and 3 <= len(rows) <= 20000, "runtime_closure")
    result: dict[str, bytes] = {}
    roles: set[str] = set()
    for row in rows:
        reject_unless(
            set(row) == {"path", "sha256", "size", "role"}
            and row["role"] in {"interpreter", "dll", "stdlib", "bootstrap"}
            and pin(row["sha256"])
            and type(row["size"]) is int
            and 0 < row["size"] <= ARCHIVE_LIMIT,
            "runtime_closure",
        )
        name = relative(row["path"])
        reject_unless(
            name.casefold() not in {key.casefold() for key in result}, "runtime_alias"
        )
        reject_unless(
            name in prepared["input"]["scope"]["allowed_read_files"]
            and _body_granted(prepared, row),
            "runtime_body_grant",
        )
        raw = read_file(located(root, name), ARCHIVE_LIMIT)
        reject_unless(
            len(raw) == row["size"] and digest(raw) == row["sha256"],
            "runtime_closure_pin",
        )
        result[name] = raw
        roles.add(row["role"])
    reject_unless(
        {"interpreter", "dll", "stdlib", "bootstrap"} <= roles,
        "runtime_closure_incomplete",
    )
    return result


def management(
    prepared: dict[str, Any], root: Path, captured: dict[str, bytes]
) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Exact independent namespace and runtime contract; no host discovery."""
    spec = document(captured["management"], MANIFEST_LIMIT)
    reject_unless(
        set(spec)
        == {
            "schema_version",
            "namespace",
            "target_roots",
            "runtime_closure",
            "qualification",
            "deployment",
        }
        and spec["schema_version"] == 1,
        "management_shape",
    )
    namespace = spec["namespace"]
    reject_unless(
        set(namespace)
        == {
            "bundle",
            "project",
            "workplace",
            "device",
            "accounting",
            "execution",
            "control",
        },
        "namespace_shape",
    )
    paths = {key: Path(value) for key, value in namespace.items()}
    for path in paths.values():
        reject_unless(
            path.is_absolute() and ".." not in path.parts, "namespace_absolute"
        )
    targets = tuple(Path(value) for value in spec["target_roots"])
    reject_unless(bool(targets) and len(set(targets)) == len(targets), "target_roots")
    for target in targets:
        reject_unless(target.is_absolute() and ".." not in target.parts, "target_root")
        for path in paths.values():
            reject_unless(
                path != target
                and path not in target.parents
                and target not in path.parents,
                "namespace_overlap",
            )
    reject_unless(paths["project"] == root, "management_project_binding")
    reject_unless(len(set(paths.values())) == len(paths), "namespace_alias")
    # The qualification record is an explicitly declared body, not an observed
    # interpreter hash or an OS-version-derived allowlist.
    q = spec["qualification"]
    reject_unless(
        set(q) == {"path", "sha256", "size"} and _body_granted(prepared, q),
        "qualification_body",
    )
    reject_unless(
        q["path"] in prepared["input"]["scope"]["allowed_read_files"],
        "qualification_scope",
    )
    binding = _native_authority(prepared["input"], identity(prepared["identity"]))
    if binding is None:
        raise Rejected("native_authority_required")
    reject_unless(
        q["sha256"] == binding["qualification_sha256"],
        "qualification_authority",
    )
    if binding["deployment"] is not None:
        reject_unless(
            digest(canonical(spec["deployment"]))
            == binding["deployment"]["spec_sha256"],
            "deployment_authority",
        )
    raw = read_file(located(root, relative(q["path"])), MANIFEST_LIMIT)
    reject_unless(
        digest(raw) == q["sha256"] and len(raw) == q["size"], "qualification_pin"
    )
    qualified = document(raw, MANIFEST_LIMIT)
    reject_unless(
        qualified.get("management_namespace") == namespace
        and qualified.get("runtime_closure_sha256")
        == digest(canonical(spec["runtime_closure"])),
        "qualification_binding",
    )
    closure = _closure(prepared, root, spec)
    interpreters = [
        row for row in spec["runtime_closure"] if row["role"] == "interpreter"
    ]
    reject_unless(
        len(interpreters) == 1
        and root / interpreters[0]["path"] == Path(sys.executable),
        "executing_runtime_not_bound",
    )
    reject_unless(
        qualified.get("runtime_version") == sys.version.split()[0], "runtime_version"
    )
    spec["qualified"] = qualified
    return spec, closure


def bind_preparation(
    prepared: dict[str, Any], root: Path, distribution: Path, driver: dict[str, Any]
) -> None:
    """First preparation only; never changes old immutable input at start."""
    job = prepared.get("input", {}).get("parameters", {}).get("native_maintenance_job")
    if job is None:
        reject_unless(
            driver.get("id") != "native-maintenance-fixed-v1", "structured_job_required"
        )
        return
    reject_unless(
        driver.get("id") == "native-maintenance-fixed-v1", "fixed_profile_required"
    )
    reject_unless(
        "maintenance" not in prepared.get("native_launch", {}), "already_prepared"
    )
    _native_authority(prepared["input"], identity(prepared["identity"]))
    prepared.setdefault("native_launch", {})["maintenance"] = {
        "runtime": job["runtime"],
        "job_sha256": digest(canonical(job)),
    }
    validate_preparation(prepared, root, distribution, driver)


def validate_preparation(
    prepared: dict[str, Any],
    root: Path,
    distribution: Path,
    driver: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    job, captured = capture_job(prepared, root)
    if driver is not None:
        # Private catalog annotations are resolution metadata; actual descriptor
        # body must equal the independently pinned source descriptor.
        supplied = {
            key: value for key, value in driver.items() if not key.startswith("_")
        }
        reject_unless(
            supplied == document(captured["descriptor"], MANIFEST_LIMIT),
            "descriptor_mismatch",
        )
    for role, name in {
        "harness": "pf_native_maintenance.py",
        "controller": "pf_cold_controller.py",
        "native": "pf_native_control.py",
        "wrapper": "prepared_executor.py",
    }.items():
        reject_unless(
            captured[role] == read_file(distribution / "tools" / name, FILE_LIMIT),
            "management_source_pin",
        )
    management(prepared, root, captured)
    return job, captured


def validate_command(
    prepared: dict[str, Any], root: Path, distribution: Path, command: dict[str, Any]
) -> None:
    """Revalidate before reservation/spawn; reject late argv/env substitutions."""
    validate_preparation(prepared, root, distribution)
    selected = identity(prepared["identity"])
    reference = command["prepared_input"]
    source = str(root / relative(reference["path"]))
    spec = command["command"]
    paths = command["paths"]
    expected = [
        sys.executable,
        "-I",
        "-B",
        str(distribution / "tools/prepared_executor.py"),
        "--prepared-input",
        source,
        "--prepared-sha256",
        reference["checksum"],
        "--heartbeat",
        str(root / paths["heartbeat"]),
        "--exit-path",
        str(root / paths["exit"]),
        "--",
        sys.executable,
        "-I",
        "-B",
        str(distribution / "tools/pf_native_maintenance.py"),
        source,
    ]
    reject_unless(
        command.get("driver_id") == "native-maintenance-fixed-v1"
        and command.get("executable_override") == ""
        and command.get("agent_model") == ""
        and command.get("agent_reasoning_effort") == "",
        "fixed_profile_required",
    )
    reject_unless(
        command["run_id"] == selected["run_id"]
        and command["task_id"] == selected["assignment_id"]
        and str(command["attempt"]) == str(selected["attempt"]),
        "command_identity",
    )
    reject_unless(
        spec.get("argv") == expected
        and spec.get("args") == expected[1:]
        and spec.get("executable") == sys.executable
        and spec.get("shell") is False
        and spec.get("environment_inherit") is False
        and spec.get("working_directory") == str(root),
        "fixed_command_mismatch",
    )
    env = spec["environment"]
    required = {
        "PF_PREPARED_INPUT_FILE": source,
        "PF_PREPARED_INPUT_SHA256": reference["checksum"],
        "PF_PROJECT_ROOT": str(root),
        "PF_RUNTIME_DRIVER_ID": "native-maintenance-fixed-v1",
        "PF_WORKER_RUN_ID": selected["run_id"],
        "PF_WORKER_TASK_ID": selected["assignment_id"],
        "PF_WORKER_ATTEMPT": str(selected["attempt"]),
        "PF_AGENT_MODEL": "",
        "PF_AGENT_REASONING_EFFORT": "",
    }
    reject_unless(
        all(env.get(key) == value for key, value in required.items()),
        "fixed_environment",
    )
    allowed = set(required) | {
        "PF_RUN_ID",
        "PF_TASK_ID",
        "PF_AGENT_RUN_DIR",
        "PF_AGENT_EXIT_PATH",
        "PF_WORKSPACE_ACCESS_FILE",
        "PF_CONFIGURATION_SNAPSHOT_PATH",
        "PF_CONFIGURATION_SNAPSHOT_SHA256",
        "SystemRoot",
        "WINDIR",
        "COMSPEC",
        "PATHEXT",
        "TEMP",
        "TMP",
    }
    reject_unless(not set(env) - allowed, "unexpected_environment")


def construct_management(
    prepared: dict[str, Any], root: Path, captured: dict[str, bytes]
) -> dict[str, Any]:
    """Build an independent accepted runtime/source bundle, create-once/resumable."""
    import fnmatch

    spec, closure = management(prepared, root, captured)
    destination = Path(spec["namespace"]["bundle"])
    scope = prepared["input"]["scope"]
    # Explicit management writes only. Target-root grants never imply this grant.
    grant = destination.relative_to(root).as_posix() + "/**"
    reject_unless(
        "write_product" in scope["allowed_actions"]
        and "write_product" not in scope.get("forbidden_actions", [])
        and grant in scope["allowed_files"],
        "bundle_write_grant",
    )
    rows = {
        "tools/"
        + {
            "harness": "pf_native_maintenance.py",
            "controller": "pf_cold_controller.py",
            "native": "pf_native_control.py",
            "wrapper": "prepared_executor.py",
        }[role]: captured[role]
        for role in ("harness", "controller", "native", "wrapper")
    }
    rows.update({"runtime/" + name: raw for name, raw in closure.items()})
    rows["management.json"] = captured["management"]
    inventory = {
        name: {"sha256": digest(raw), "size": len(raw)} for name, raw in rows.items()
    }
    destinations = [
        (destination / name).relative_to(root).as_posix()
        for name in (*rows, "bundle.json")
    ]
    reject_unless(
        not any(
            fnmatch.fnmatchcase(name.casefold(), pattern.casefold())
            for name in destinations
            for pattern in scope.get("forbidden_files", [])
        ),
        "bundle_write_grant",
    )
    destination.mkdir(parents=True, exist_ok=True)
    for name, raw in rows.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        publish(destination, name, raw)
    publish(destination, "bundle.json", canonical(inventory))
    return {"bundle_sha256": digest(canonical(inventory)), "files": len(rows)}


def execute(prepared: dict[str, Any], root: Path) -> tuple[str, bytes]:
    job, captured = capture_job(prepared, root)
    spec, _ = management(prepared, root, captured)
    operation = job["operation"]
    if operation == "qualify-archive":
        summary = qualify_archive(captured["archive"], captured["manifest"])
    elif operation == "construct-management":
        summary = construct_management(prepared, root, captured)
    else:
        # Captured management code is independent of inhibited target imports.
        native = _captured_module(
            "pf_native_control", captured["native"], str(root / "accepted-native.py")
        )
        controller = _captured_module(
            "pf_cold_controller",
            captured["controller"],
            str(root / "accepted-controller.py"),
        )
        summary = controller.execute_job(operation, spec, captured, native)
    return job["report"], canonical(
        {
            "schema_version": 1,
            "identity": job["identity"],
            "operation": operation,
            "result": "pass",
            "summary": summary,
            "actual_provider_qualified": False,
            "production_ready": False,
        }
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
