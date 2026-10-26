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
import unicodedata
import zipfile
import zlib
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
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
    reject_unless(
        unicodedata.normalize("NFC", value) == value
        and len(value.encode("utf-8")) <= 1024
        and not any(ord(c) < 32 or ord(c) == 127 or c in '<>"|?*' for c in value),
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


def qualify_archive(archive: bytes, manifest: bytes, native: Any) -> dict[str, Any]:
    """Use the unchanged native Core parser/seal/inventory on release bytes."""
    reject_unless(len(manifest) <= MANIFEST_LIMIT, "manifest_size")
    expected = native.parse_manifest(manifest)
    reject_unless(len(expected["files"]) < ENTRY_LIMIT, "archive_entries")
    files = {row["relative_path"]: row for row in expected["files"]}
    reject_unless(
        all(row["size"] <= FILE_LIMIT for row in files.values())
        and sum(row["size"] for row in files.values()) + len(manifest)
        <= EXPANDED_LIMIT,
        "archive_expansion",
    )
    stream = io.BytesIO(archive)
    _zip_preflight(stream)
    payload = {}
    try:
        with zipfile.ZipFile(stream) as package:
            reject_unless(
                set(package.namelist()) == set(files) | {native.MANIFEST}
                and len(package.infolist()) == len(files) + 1,
                "archive_membership",
            )
            for entry in package.infolist():
                expected_size = (
                    len(manifest)
                    if entry.filename == native.MANIFEST
                    else files[entry.filename]["size"]
                )
                reject_unless(entry.file_size == expected_size, "archive_expansion")
                with package.open(entry) as member:
                    raw = member.read(expected_size + 1)
                reject_unless(len(raw) == expected_size, "archive_expansion")
                if entry.filename == native.MANIFEST:
                    reject_unless(raw == manifest, "embedded_manifest_mismatch")
                else:
                    reject_unless(
                        native.digest(raw) == files[entry.filename]["sha256"],
                        "archive_digest",
                    )
                    payload[entry.filename] = raw
    except (
        zipfile.BadZipFile,
        zlib.error,
        NotImplementedError,
        RuntimeError,
        EOFError,
    ):
        raise Rejected("archive_invalid") from None
    reject_unless(
        native.leaf_seal(payload[native.LEAF])
        == (native.SEAL_KIND, native.digest(native.projection(manifest))),
        "archive_leaf_seal",
    )
    reject_unless(
        payload[native.INVENTORY] == native.inventory_bytes(payload),
        "archive_inventory",
    )
    return {
        "files": len(files),
        "expanded_bytes": sum(r["size"] for r in files.values()),
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
    import unicodedata

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
                "material",
            }
        )
        require(type(value["schema_version"]) is int and value["schema_version"] == 2)
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
        material_shape(value["material"])
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

    def portable(name: Any) -> str:
        require(isinstance(name, str) and 0 < len(name.encode("utf-8")) <= 1024)
        require(unicodedata.normalize("NFC", name) == name)
        require(not any(ord(c) < 32 or ord(c) == 127 or c in '\\:<>"|?*' for c in name))
        require(
            all(
                part not in {"", ".", ".."}
                and not part.endswith((".", " "))
                and re.fullmatch(
                    r"(?i:con|prn|aux|nul|conin\$|conout\$|com[0-9]|lpt[0-9])",
                    part.split(".")[0],
                )
                is None
                for part in name.split("/")
            )
        )
        return str(name)

    def material_shape(value: Any) -> None:
        require(
            isinstance(value, dict)
            and set(value)
            == {
                "schema_version",
                "body_manifest",
                "roots",
                "permission",
                "capture",
                "quotas",
            },
            "native_material_shape",
        )
        require(type(value["schema_version"]) is int and value["schema_version"] == 1)
        require(value["permission"] == "body-and-qualified-runtime-load")
        manifest = value["body_manifest"]
        require(
            isinstance(manifest, dict)
            and set(manifest) == {"resource_id", "path", "sha256", "size"}
        )
        require(
            isinstance(manifest["resource_id"], str)
            and re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", manifest["resource_id"])
            is not None
        )
        portable(manifest["path"])
        require(
            pinned(manifest["sha256"])
            and type(manifest["size"]) is int
            and 0 < manifest["size"] <= 1048576
        )
        roots = value["roots"]
        require(isinstance(roots, list) and len(roots) == 2)
        prefixes = {}
        for row in roots:
            require(
                isinstance(row, dict) and set(row) == {"id", "base", "relative_path"}
            )
            require(
                isinstance(row["id"], str)
                and row["id"] in {"archive", "runtime"}
                and row["id"] not in prefixes
                and row["base"] == "project"
            )
            prefixes[row["id"]] = portable(row["relative_path"]).casefold()
        left, right = prefixes["archive"], prefixes["runtime"]
        require(
            left != right
            and not left.startswith(right + "/")
            and not right.startswith(left + "/")
        )
        capture = value["capture"]
        require(isinstance(capture, dict) and set(capture) == {"directory", "access"})
        portable(capture["directory"])
        require(capture["access"] == ["create_once", "read", "remove_own_partial"])
        ceilings = {
            "manifest_bytes": 1048576,
            "receipt_index_bytes": 1048576,
            "members": 4096,
            "root_prefixes": 2,
            "path_utf8_bytes": 1024,
            "resource_id_bytes": 160,
            "member_bytes": 134217728,
            "interpreter_bytes": 33554432,
            "total_material_bytes": 536870912,
            "copy_chunk_bytes": 65536,
            "capture_working_buffer_bytes": 1048576,
            "capture_metadata_accounted_bytes": 16777216,
            "capture_directory_disk_bytes": 536870912,
            "zip_central_directory_bytes": 4194304,
            "zip_header_member_bytes": 16384,
            "zip_header_total_bytes": 4194304,
            "zip_tail_probe_bytes": 65557,
            "native_consumer_payload_reservation_bytes": 2147483648,
        }
        quotas = value["quotas"]
        require(isinstance(quotas, dict) and set(quotas) == set(ceilings))
        for key, maximum in ceilings.items():
            require(type(quotas[key]) is int and 0 < quotas[key] <= maximum)
            if key != "native_consumer_payload_reservation_bytes":
                require(quotas[key] == maximum)

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
    require(type(job["schema_version"]) is int and job["schema_version"] == 2)
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
        and policy["schema_version"] == 2
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
    material = binding["material"]
    capture = material["capture"]["directory"]
    ident = binding["identity"]
    require(
        capture
        == ".pf/runtime/agent-runs/"
        + ident["run_id"]
        + "/"
        + ident["assignment_id"]
        + "/attempts/"
        + str(ident["attempt"])
        + "/native-material",
        "native_capture_attempt",
    )
    require(
        permitted(capture + "/**", "write_artifact", "allowed_files")
        and permitted(capture + "/**", "read", "allowed_read_files"),
        "native_capture_scope",
    )
    manifest = material["body_manifest"]
    require(
        permitted(manifest["path"], "read", "allowed_read_files"),
        "native_material_manifest_scope",
    )
    declarations = [
        row
        for row in semantic.get("sources", [])
        if isinstance(row, dict) and row.get("path") == manifest["path"]
    ]
    require(
        len(declarations) == 1
        and declarations[0].get("status") == "available"
        and declarations[0].get("checksum") == manifest["sha256"]
        and declarations[0].get("size") == manifest["size"],
        "native_material_manifest_body",
    )
    if selected is not None:
        require(
            declarations[0].get("delivery") in {"inline", "reference"},
            "native_material_manifest_body",
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
        name = portable(row["path"])
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
        by_role[row["role"]] = row
        names.add(name.casefold())
        if row["role"] == "archive":
            prefix = next(
                r["relative_path"] for r in material["roots"] if r["id"] == "archive"
            )
            require(name.startswith(prefix + "/"), "native_material_archive_root")
            continue
        require(row["size"] <= 1048576, "native_small_source_limit")
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


def _material_request(prepared: dict[str, Any]) -> dict[str, Any]:
    binding = _native_authority(prepared["input"], identity(prepared["identity"]))
    reject_unless(binding is not None, "native_authority_required")
    if binding is None:
        raise Rejected("native_authority_required")
    return dict(binding["material"])


def _material_plan(
    prepared: dict[str, Any], root: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Admit the entire finite set before opening any native member."""
    import fnmatch

    request = _material_request(prepared)
    row = request["body_manifest"]
    reject_unless(_body_granted(prepared, row), "material_manifest_body")
    raw = read_file(located(root, row["path"]), MANIFEST_LIMIT)
    reject_unless(
        len(raw) == row["size"] and digest(raw) == row["sha256"],
        "material_manifest_pin",
    )
    manifest = document(raw, MANIFEST_LIMIT)
    reject_unless(
        set(manifest) == {"schema_version", "kind", "members"}
        and type(manifest["schema_version"]) is int
        and manifest["schema_version"] == 1
        and manifest["kind"] == "pf.native-material.manifest",
        "material_manifest_shape",
    )
    members = manifest["members"]
    reject_unless(
        isinstance(members, list) and 5 <= len(members) <= ENTRY_LIMIT,
        "material_members",
    )
    job = prepared["input"]["parameters"]["native_maintenance_job"]
    small = {r["role"]: r for r in job["resources"]}
    management_row = small["management"]
    reject_unless(_body_granted(prepared, management_row), "management_body")
    raw_spec = read_file(located(root, management_row["path"]), MANIFEST_LIMIT)
    reject_unless(
        digest(raw_spec) == management_row["sha256"]
        and len(raw_spec) == management_row["size"],
        "management_pin",
    )
    spec = document(raw_spec, MANIFEST_LIMIT)
    reject_unless(isinstance(spec.get("runtime_closure"), list), "runtime_closure")
    roots = {r["id"]: r["relative_path"] for r in request["roots"]}
    scope = prepared["input"]["scope"]
    capture = request["capture"]["directory"]
    for name in (capture, capture + "/index.json", capture + "/archive.snapshot"):
        reject_unless(
            not any(
                fnmatch.fnmatchcase(name.casefold(), pattern.casefold())
                for pattern in scope.get("forbidden_files", [])
            ),
            "material_capture_denied",
        )
    reject_unless(
        all(
            not (
                capture.casefold() == prefix.casefold()
                or capture.casefold().startswith(prefix.casefold() + "/")
                or prefix.casefold().startswith(capture.casefold() + "/")
            )
            for prefix in roots.values()
        ),
        "material_capture_overlap",
    )
    names = {r["path"].casefold() for r in job["resources"] if r["role"] != "archive"}
    names.add(row["path"].casefold())
    names.add(job["report"].casefold())
    ids: set[str] = set()
    runtime = []
    roles = []
    total = 0
    archive_size = 0
    for member in members:
        reject_unless(
            isinstance(member, dict)
            and set(member)
            == {"resource_id", "role", "root_id", "path", "size", "sha256"},
            "material_member_shape",
        )
        name = relative(member["path"])
        rid = member["resource_id"]
        role = member["role"]
        reject_unless(
            isinstance(rid, str)
            and re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", rid) is not None
            and rid.casefold() not in ids
            and name.casefold() not in names,
            "material_alias",
        )
        reject_unless(
            isinstance(role, str)
            and role in {"archive", "interpreter", "dll", "stdlib", "bootstrap"}
            and member["root_id"] == ("archive" if role == "archive" else "runtime"),
            "material_role",
        )
        reject_unless(
            name.startswith(roots[member["root_id"]] + "/")
            and pin(member["sha256"])
            and type(member["size"]) is int
            and 0
            < member["size"]
            <= (FILE_LIMIT if role == "interpreter" else ARCHIVE_LIMIT),
            "material_member_bounds",
        )
        reject_unless(
            name in scope.get("allowed_read_files", [])
            and not any(
                fnmatch.fnmatchcase(name.casefold(), pattern.casefold())
                for pattern in scope.get("forbidden_files", [])
            ),
            "material_member_scope",
        )
        reject_unless(
            not any(
                name.casefold().startswith(other + "/")
                or other.startswith(name.casefold() + "/")
                for other in names
            ),
            "material_path_collision",
        )
        names.add(name.casefold())
        ids.add(rid.casefold())
        roles.append(role)
        total += member["size"]
        if role == "archive":
            archive_size = member["size"]
            reject_unless(
                {k: member[k] for k in ("path", "sha256", "size")}
                == {k: small["archive"][k] for k in ("path", "sha256", "size")},
                "material_archive_binding",
            )
        else:
            runtime.append({k: member[k] for k in ("path", "sha256", "size", "role")})
    reject_unless(
        roles.count("archive") == 1
        and roles.count("interpreter") == 1
        and {"dll", "stdlib", "bootstrap"} <= set(roles),
        "material_role_set",
    )
    reject_unless(runtime == spec["runtime_closure"], "material_runtime_binding")
    interpreter = next(r for r in runtime if r["role"] == "interpreter")
    reject_unless(
        root / interpreter["path"] == Path(sys.executable),
        "executing_runtime_not_bound",
    )
    reject_unless(
        interpreter["sha256"] == job["runtime"]["sha256"], "runtime_pin_mismatch"
    )
    reject_unless(total <= request["quotas"]["total_material_bytes"], "material_total")
    # Charge conservative per-row Python metadata plus raw manifest/index and buffers.
    reject_unless(
        len(members) * 3072 + 2 * len(raw)
        <= request["quotas"]["capture_metadata_accounted_bytes"],
        "material_metadata_budget",
    )
    reject_unless(
        archive_size + MANIFEST_LIMIT
        <= request["quotas"]["capture_directory_disk_bytes"],
        "material_disk_budget",
    )
    q = spec.get("qualification", {})
    reject_unless(
        isinstance(q, dict)
        and set(q) == {"path", "sha256", "size"}
        and _body_granted(prepared, q),
        "qualification_body",
    )
    qraw = read_file(located(root, relative(q["path"])), MANIFEST_LIMIT)
    reject_unless(
        len(qraw) == q["size"] and digest(qraw) == q["sha256"], "qualification_pin"
    )
    qualified = document(qraw, MANIFEST_LIMIT)
    binding = _native_authority(prepared["input"], prepared["identity"])
    reject_unless(
        binding is not None and q["sha256"] == binding["qualification_sha256"],
        "qualification_authority",
    )
    reject_unless(
        qualified.get("management_namespace") == spec.get("namespace")
        and qualified.get("runtime_closure_sha256") == digest(canonical(runtime))
        and qualified.get("runtime_version") == sys.version.split()[0],
        "qualification_binding",
    )
    namespace = spec.get("namespace")
    reject_unless(
        isinstance(namespace, dict)
        and set(namespace)
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
    if not isinstance(namespace, dict):
        raise Rejected("namespace_shape")
    paths = [Path(value) for value in namespace.values()]
    reject_unless(
        all(path.is_absolute() and ".." not in path.parts for path in paths)
        and len(set(paths)) == 7,
        "namespace_alias",
    )
    reject_unless(namespace["project"] == str(root), "management_project_binding")
    targets = spec.get("target_roots")
    reject_unless(isinstance(targets, list) and 0 < len(targets) <= 128, "target_roots")
    if not isinstance(targets, list):
        raise Rejected("target_roots")
    targets = [Path(value) for value in targets]
    reject_unless(
        all(t.is_absolute() and ".." not in t.parts for t in targets), "target_root"
    )
    for target in targets:
        reject_unless(
            all(
                target != path
                and target not in path.parents
                and path not in target.parents
                for path in paths
            ),
            "namespace_overlap",
        )
        reject_unless(
            all(
                target == other
                or (target not in other.parents and other not in target.parents)
                for other in targets
            ),
            "target_overlap",
        )
    return request, members


def _file_identity(info: os.stat_result) -> dict[str, int]:
    return {
        "volume": info.st_dev,
        "file_id": info.st_ino,
        "size": info.st_size,
        "mtime_ns": info.st_mtime_ns,
        "ctime_ns": info.st_ctime_ns,
    }


@contextmanager
def _safe_material_file(
    root: Path, name: str, *, create: bool = False, directory: bool = False
) -> Iterator[Any]:
    """Hold Windows ancestors and a no-write/delete-sharing regular file.

    Fail closed on other backends. Protected namespace/parent ACL qualification
    remains independent; these handles do not establish the issuer's legitimacy.
    """
    import ctypes
    import msvcrt
    from ctypes import wintypes

    reject_unless(os.name == "nt", "material_backend_unsupported")
    path = root if directory and not name else root / relative(name)
    reject_unless(
        root.is_absolute() and not root.drive.startswith("\\\\"), "material_root"
    )
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.GetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel.GetFinalPathNameByHandleW.argtypes = [
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    ]

    class Info(ctypes.Structure):
        _fields_ = [
            ("attributes", wintypes.DWORD),
            ("created", wintypes.FILETIME),
            ("accessed", wintypes.FILETIME),
            ("written", wintypes.FILETIME),
            ("volume", wintypes.DWORD),
            ("size_high", wintypes.DWORD),
            ("size_low", wintypes.DWORD),
            ("links", wintypes.DWORD),
            ("index_high", wintypes.DWORD),
            ("index_low", wintypes.DWORD),
        ]

    handles = []
    try:
        for item in (*reversed(path.parents), path):
            is_file = item == path and not directory
            handle = kernel.CreateFileW(
                str(item),
                0xC0000000 if create and is_file else (0x80000000 if is_file else 0x80),
                1 if is_file else 3,
                None,
                1 if create and is_file else 3,
                0x00200000 | (0 if is_file else 0x02000000),
                None,
            )
            if handle == ctypes.c_void_p(-1).value:
                raise OSError(ctypes.get_last_error(), "material_handle_denied")
            handles.append(handle)
            info = Info()
            reject_unless(
                bool(kernel.GetFileInformationByHandle(handle, ctypes.byref(info))),
                "material_handle_info",
            )
            reject_unless(
                not info.attributes & (0x400 | 0x200)
                and (
                    not info.attributes & 0x10 and info.links == 1
                    if is_file
                    else bool(info.attributes & 0x10)
                ),
                "material_redirected",
            )
            buffer = ctypes.create_unicode_buffer(32768)
            length = kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
            reject_unless(0 < length < len(buffer), "material_final_path")
            actual = buffer.value.removeprefix("\\\\?\\")
            reject_unless(
                actual.casefold().rstrip("\\") == str(item).casefold().rstrip("\\"),
                "material_path_alias",
            )
        if directory:
            yield _file_identity(path.stat())
            return
        fd = msvcrt.open_osfhandle(
            int(handles.pop()), os.O_BINARY | (os.O_RDWR if create else os.O_RDONLY)
        )
        with os.fdopen(fd, "w+b" if create else "rb") as stream:
            before = os.fstat(stream.fileno())
            reject_unless(
                stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
                "material_regular",
            )
            yield stream
            after = os.fstat(stream.fileno())
            if not create:
                reject_unless(
                    _file_identity(before) == _file_identity(after), "material_changed"
                )
                # Windows path stat may expose birth time as ctime while fstat
                # exposes NT change time. Compare change time only handle-to-handle.
                final = _file_identity(path.stat())
                reject_unless(
                    all(
                        _file_identity(after)[key] == final[key]
                        for key in ("volume", "file_id", "size", "mtime_ns")
                    ),
                    "material_replaced",
                )
    finally:
        for handle in reversed(handles):
            kernel.CloseHandle(handle)


def _stream_material(stream: Any, row: dict[str, Any], target: Any = None) -> None:
    before = os.fstat(stream.fileno())
    reject_unless(before.st_size == row["size"], "material_size")
    hashed = hashlib.sha256()
    count = 0
    while chunk := stream.read(65536):
        count += len(chunk)
        reject_unless(count <= row["size"], "material_growth")
        hashed.update(chunk)
        if target is not None:
            reject_unless(target.write(chunk) == len(chunk), "material_short_write")
    reject_unless(
        count == row["size"] and "sha256:" + hashed.hexdigest() == row["sha256"],
        "material_pin",
    )
    reject_unless(
        _file_identity(before) == _file_identity(os.fstat(stream.fileno())),
        "material_changed",
    )


def _material_index_paths(request: dict[str, Any]) -> tuple[str, str]:
    directory = request["capture"]["directory"]
    return directory + "/index.json", directory + "/archive.snapshot"


def _material_receipt(
    prepared: dict[str, Any], request: dict[str, Any], index: dict[str, Any], raw: bytes
) -> dict[str, Any]:
    name, _ = _material_index_paths(request)
    return {
        "schema_version": 1,
        "kind": "pf.native-material.available-body",
        "identity": identity(prepared["identity"]),
        "job_sha256": digest(
            canonical(prepared["input"]["parameters"]["native_maintenance_job"])
        ),
        "manifest_sha256": request["body_manifest"]["sha256"],
        "request_sha256": digest(canonical(request)),
        "index": {"path": name, "sha256": digest(raw), "size": len(raw)},
        "totals": index["totals"],
    }


def capture_material(prepared: dict[str, Any], root: Path) -> dict[str, Any]:
    """Producer only. An interrupted create is retained, never made available."""
    request, members = _material_plan(prepared, root)
    index_name, snapshot = _material_index_paths(request)
    directory = root / request["capture"]["directory"]
    # This exact attempt namespace is never enumerated/cleaned to recover a retry.
    if directory.exists():
        reject_unless((root / index_name).is_file(), "material_partial")
        with _safe_material_file(root, index_name) as stream:
            raw = stream.read(MANIFEST_LIMIT + 1)
        index = document(raw, MANIFEST_LIMIT)
        receipt = _material_receipt(prepared, request, index, raw)
        validate_material(prepared, root, receipt)
        return receipt
    # Create only exact authorized ancestry, checking each existing component.
    parent = root
    for part in relative(request["capture"]["directory"]).split("/"):
        parent /= part
        if not parent.exists():
            parent_name = parent.parent.relative_to(root).as_posix()
            with _safe_material_file(
                root, "" if parent_name == "." else parent_name, directory=True
            ):
                parent.mkdir()
        _plain(parent, file=False)
    import shutil

    archive = next(row for row in members if row["role"] == "archive")
    reject_unless(
        shutil.disk_usage(directory).free >= archive["size"] + MANIFEST_LIMIT,
        "material_disk_free",
    )
    index_rows = []
    aliases: set[tuple[int, int]] = set()
    for row in members:
        with _safe_material_file(root, row["path"]) as stream:
            info = _file_identity(os.fstat(stream.fileno()))
            key = (info["volume"], info["file_id"])
            reject_unless(key not in aliases, "material_file_alias")
            aliases.add(key)
            prefix = next(
                r["relative_path"]
                for r in request["roots"]
                if r["id"] == row["root_id"]
            )
            root_info = _file_identity((root / prefix).stat())
            if row["role"] == "archive":
                with _safe_material_file(root, snapshot, create=True) as target:
                    _stream_material(stream, row, target)
                    target.flush()
                    os.fsync(target.fileno())
                reference = snapshot
                mode = "captured_copy"
                with _safe_material_file(root, snapshot) as frozen:
                    reference_info = _file_identity(os.fstat(frozen.fileno()))
            else:
                _stream_material(stream, row)
                reference, mode = row["path"], "protected_reference"
                reference_info = info
        index_rows.append(
            {
                "resource_id": row["resource_id"],
                "role": row["role"],
                "source_path": row["path"],
                "source_identity": {"original": info, "reference": reference_info},
                "root_identity": root_info,
                "mode": mode,
                "reference_path": reference,
                "size": row["size"],
                "sha256": row["sha256"],
            }
        )
    index = {
        "schema_version": 1,
        "kind": "pf.native-material.index",
        "identity": identity(prepared["identity"]),
        "job_sha256": digest(
            canonical(prepared["input"]["parameters"]["native_maintenance_job"])
        ),
        "manifest_sha256": request["body_manifest"]["sha256"],
        "request_sha256": digest(canonical(request)),
        "members": index_rows,
        "totals": {"files": len(members), "bytes": sum(r["size"] for r in members)},
    }
    raw = canonical(index)
    reject_unless(len(raw) <= MANIFEST_LIMIT, "material_index_limit")
    receipt = _material_receipt(prepared, request, index, raw)
    # Validate original + captured archive and bounded ZIP before commit marker.
    _validate_material_members(root, request, members, index)
    with _safe_material_file(root, snapshot) as stream:
        _zip_preflight(stream)
    with _safe_material_file(root, index_name, create=True) as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return receipt


def _validate_material_members(
    root: Path,
    request: dict[str, Any],
    members: list[dict[str, Any]],
    index: dict[str, Any],
) -> None:
    reject_unless(
        isinstance(index.get("members"), list)
        and len(index["members"]) == len(members),
        "material_index_members",
    )
    _, snapshot = _material_index_paths(request)
    aliases: set[tuple[int, int]] = set()
    for row, saved in zip(members, index["members"], strict=True):
        reject_unless(
            isinstance(saved, dict)
            and set(saved)
            == {
                "resource_id",
                "role",
                "source_path",
                "source_identity",
                "root_identity",
                "mode",
                "reference_path",
                "size",
                "sha256",
            },
            "material_index_row",
        )
        reject_unless(
            isinstance(saved["source_identity"], dict)
            and set(saved["source_identity"]) == {"original", "reference"},
            "material_identity_shape",
        )
        for item in (
            saved["source_identity"]["original"],
            saved["source_identity"]["reference"],
            saved["root_identity"],
        ):
            reject_unless(
                isinstance(item, dict)
                and set(item) == {"volume", "file_id", "size", "mtime_ns", "ctime_ns"}
                and all(type(value) is int and value >= 0 for value in item.values()),
                "material_identity_shape",
            )
        reject_unless(
            all(
                saved.get(k) == row[k]
                for k in ("resource_id", "role", "size", "sha256")
            )
            and saved["source_path"] == row["path"]
            and saved["mode"]
            == ("captured_copy" if row["role"] == "archive" else "protected_reference")
            and saved["reference_path"]
            == (snapshot if row["role"] == "archive" else row["path"]),
            "material_reference_binding",
        )
        with _safe_material_file(root, row["path"]) as source:
            actual = _file_identity(os.fstat(source.fileno()))
            reject_unless(
                actual == saved["source_identity"]["original"],
                "material_source_identity",
            )
            key = (actual["volume"], actual["file_id"])
            reject_unless(key not in aliases, "material_file_alias")
            aliases.add(key)
            prefix = next(
                r["relative_path"]
                for r in request["roots"]
                if r["id"] == row["root_id"]
            )
            current_root = _file_identity((root / prefix).stat())
            # Directory mtime changes when files are added; identity is physical.
            reject_unless(
                all(
                    current_root[k] == saved["root_identity"].get(k)
                    for k in ("volume", "file_id")
                ),
                "material_root_identity",
            )
            _stream_material(source, row)
        if row["role"] == "archive":
            with _safe_material_file(root, snapshot) as stream:
                reject_unless(
                    _file_identity(os.fstat(stream.fileno()))
                    == saved["source_identity"]["reference"],
                    "material_snapshot_identity",
                )
                _stream_material(stream, row)


def validate_material(
    prepared: dict[str, Any], root: Path, receipt: Any = None
) -> list[dict[str, Any]]:
    """Read-only consumer. Never creates a receipt or repairs partial capture."""
    request, members = _material_plan(prepared, root)
    if receipt is None:
        receipt = (
            prepared.get("native_launch", {}).get("maintenance", {}).get("material")
        )
    reject_unless(
        isinstance(receipt, dict)
        and set(receipt)
        == {
            "schema_version",
            "kind",
            "identity",
            "job_sha256",
            "manifest_sha256",
            "request_sha256",
            "index",
            "totals",
        },
        "material_receipt_required",
    )
    index_name, _ = _material_index_paths(request)
    pin_row = receipt["index"]
    reject_unless(
        isinstance(pin_row, dict)
        and set(pin_row) == {"path", "sha256", "size"}
        and pin_row["path"] == index_name
        and pin(pin_row["sha256"])
        and type(pin_row["size"]) is int
        and 0 < pin_row["size"] <= MANIFEST_LIMIT,
        "material_index_reference",
    )
    with _safe_material_file(root, index_name) as stream:
        raw = stream.read(MANIFEST_LIMIT + 1)
    reject_unless(
        len(raw) == pin_row["size"] and digest(raw) == pin_row["sha256"],
        "material_index_pin",
    )
    index = document(raw, MANIFEST_LIMIT)
    reject_unless(
        set(index)
        == {
            "schema_version",
            "kind",
            "identity",
            "job_sha256",
            "manifest_sha256",
            "request_sha256",
            "members",
            "totals",
        }
        and type(index["schema_version"]) is int
        and index["schema_version"] == 1
        and index["kind"] == "pf.native-material.index",
        "material_index_shape",
    )
    reject_unless(
        isinstance(receipt["totals"], dict)
        and set(receipt["totals"]) == {"files", "bytes"}
        and all(type(v) is int for v in receipt["totals"].values()),
        "material_totals_shape",
    )
    expected = _material_receipt(prepared, request, index, raw)
    reject_unless(
        type(receipt["schema_version"]) is int and receipt == expected,
        "material_receipt_binding",
    )
    reject_unless(
        all(
            index[k] == expected[k]
            for k in ("identity", "job_sha256", "manifest_sha256", "request_sha256")
        )
        and index["totals"]
        == {"files": len(members), "bytes": sum(r["size"] for r in members)},
        "material_index_binding",
    )
    _validate_material_members(root, request, members, index)
    return members


def _zip_preflight(stream: Any) -> None:
    """Bound EOCD, central and local headers before ZipFile allocates metadata."""
    import struct

    stream.seek(0, 2)
    size = stream.tell()
    reject_unless(22 <= size <= ARCHIVE_LIMIT, "archive_size")
    stream.seek(max(0, size - 65557))
    tail = stream.read(65557)
    offset = tail.rfind(b"PK\x05\x06")
    reject_unless(offset >= 0 and offset + 22 <= len(tail), "zip_eocd")
    _, disk, cd_disk, disk_count, count, cd_size, cd_offset, comment = (
        struct.unpack_from("<4s4H2IH", tail, offset)
    )
    reject_unless(
        disk == cd_disk == 0
        and disk_count == count
        and 0 < count <= ENTRY_LIMIT
        and count != 65535
        and cd_size <= 4194304
        and cd_offset + cd_size == size - len(tail) + offset
        and offset + 22 + comment == len(tail),
        "zip_directory_bounds",
    )
    stream.seek(cd_offset)
    central = stream.read(cd_size)
    reject_unless(len(central) == cd_size, "zip_directory_short")
    pos = 0
    spans = []
    names: set[str] = set()
    expanded = 0
    header_total = 0
    for _ in range(count):
        reject_unless(pos + 46 <= len(central), "zip_central_header")
        fields = struct.unpack_from("<4s6H3I5H2I", central, pos)
        (
            sig,
            _,
            _,
            flags,
            method,
            _,
            _,
            crc,
            compressed,
            plain,
            nlen,
            xlen,
            clen,
            disk,
            _,
            external,
            local,
        ) = fields
        length = 46 + nlen + xlen + clen
        reject_unless(
            sig == b"PK\x01\x02"
            and length <= 16384
            and pos + length <= len(central)
            and not flags & (1 | 8 | 0x20 | 0x40 | 0x2000)
            and method in {0, 8}
            and disk == 0
            and max(compressed, plain, local) < 0xFFFFFFFF
            and plain <= FILE_LIMIT
            and not external & 0x410
            and stat.S_IFMT(external >> 16) in {0, stat.S_IFREG},
            "zip_central_header",
        )
        name_raw = central[pos + 46 : pos + 46 + nlen]
        name = relative(name_raw.decode("utf-8" if flags & 0x800 else "cp437"))
        reject_unless(name.casefold() not in names, "zip_alias")
        names.add(name.casefold())
        extra = central[pos + 46 + nlen : pos + 46 + nlen + xlen]
        _zip_extra(extra)
        stream.seek(local)
        header = stream.read(30)
        reject_unless(len(header) == 30, "zip_local_header")
        lsig, _, lflags, lmethod, _, _, lcrc, lc, lp, ln, lx = struct.unpack(
            "<4s5H3I2H", header
        )
        reject_unless(
            lsig == b"PK\x03\x04"
            and (lflags, lmethod, lcrc, lc, lp, ln)
            == (flags, method, crc, compressed, plain, nlen)
            and 30 + ln + lx <= 16384
            and local + 30 + ln + lx + compressed <= cd_offset,
            "zip_local_header",
        )
        reject_unless(stream.read(ln) == name_raw, "zip_local_name")
        _zip_extra(stream.read(lx))
        spans.append((local, local + 30 + ln + lx + compressed))
        header_total += length + 30 + ln + lx
        expanded += plain
        reject_unless(
            expanded <= EXPANDED_LIMIT and header_total <= 4194304, "zip_totals"
        )
        pos += length
    reject_unless(pos == len(central), "zip_directory_trailing")
    end = 0
    for first, last in sorted(spans):
        reject_unless(first == end, "zip_overlap_or_gap")
        end = last
    reject_unless(end == cd_offset, "zip_payload_trailing")
    stream.seek(0)


def _zip_extra(raw: bytes) -> None:
    import struct

    offset = 0
    while offset < len(raw):
        reject_unless(offset + 4 <= len(raw), "zip_extra")
        kind, size = struct.unpack_from("<HH", raw, offset)
        offset += 4 + size
        reject_unless(kind != 1 and offset <= len(raw), "zip64_or_extra")


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
        and job["schema_version"] == 2
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
    marker = prepared.get("native_launch", {}).get("maintenance", {})
    reject_unless(
        set(marker) == {"runtime", "job_sha256", "material"}
        and marker["runtime"] == runtime
        and marker["job_sha256"] == digest(canonical(job)),
        "runtime_body_grant_required",
    )
    validate_material(prepared, root)
    rows = job["resources"]
    reject_unless(isinstance(rows, list) and len(rows) == len(ROLES), "resource_roles")
    request = _material_request(prepared)
    archive_row = next(r for r in rows if r["role"] == "archive")
    # BytesIO + FrozenArchive + base64/JSON parent+child + simultaneous images.
    _, snapshot = _material_index_paths(request)
    with _safe_material_file(root, snapshot) as stream:
        _zip_preflight(stream)
        with zipfile.ZipFile(stream) as package:
            expanded = sum(entry.file_size for entry in package.infolist())
    peak = (
        archive_row["size"] * 8
        + expanded * 10
        + sum(r["size"] for r in rows if r["role"] != "archive") * 4
    )
    reject_unless(
        peak <= request["quotas"]["native_consumer_payload_reservation_bytes"],
        "native_payload_peak",
    )
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
        if row["role"] == "archive":
            request = _material_request(prepared)
            _, snapshot = _material_index_paths(request)
            with _safe_material_file(root, snapshot) as stream:
                _zip_preflight(stream)
                raw = stream.read(ARCHIVE_LIMIT + 1)
            reject_unless(
                len(raw) == row["size"] and digest(raw) == row["sha256"],
                "material_snapshot_pin",
            )
            captured["archive"] = raw
            continue
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
) -> dict[str, dict[str, Any]]:
    """Validate protected runtime references without accumulating their bytes."""
    members = validate_material(prepared, root)
    runtime = [
        {k: row[k] for k in ("path", "sha256", "size", "role")}
        for row in members
        if row["role"] != "archive"
    ]
    reject_unless(runtime == spec["runtime_closure"], "runtime_closure_pin")
    return {row["path"]: row for row in runtime}


def management(
    prepared: dict[str, Any], root: Path, captured: dict[str, bytes]
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
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
        "material": capture_material(prepared, root),
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


@contextmanager
def _hold_material_references(prepared: dict[str, Any], root: Path) -> Iterator[None]:
    """Retain qualified references and small bodies through their consumer."""
    request, members = _material_plan(prepared, root)
    index, snapshot = _material_index_paths(request)
    names = [index, snapshot, *(row["path"] for row in members)]
    names.extend(
        row["path"]
        for row in prepared["input"]["sources"]
        if row.get("status") == "available"
    )
    with ExitStack() as held:
        for name in dict.fromkeys(names):
            held.enter_context(_safe_material_file(root, name))
        yield


@contextmanager
def hold_start_material(
    prepared: dict[str, Any], root: Path, distribution: Path, command: dict[str, Any]
) -> Iterator[Any]:
    """Validate outside admission, retaining actual handles through spawn.

    Core must already hold current policy/semantic inputs while loading prepared.
    This layer owns material IO and cannot turn a caller receipt into authority.
    """
    import pf_native_control as native

    with ExitStack() as held:
        entry = native.current_entry()
        held.enter_context(native.operation_lease())
        if entry is not None and entry.control is not None:
            # The native lease already owns the writable guard handle. Do not
            # reopen it with a sharing mode incompatible with that live lease.
            authority_paths = [entry.control.epoch_path]
            if entry.control.guard.name == "installation.guard":
                authority_paths.append(
                    entry.control.guard.parent.parent / "managed-ingress/adoption.json"
                )
            for path in authority_paths:
                held.enter_context(
                    _safe_material_file(
                        Path(path.anchor), path.relative_to(path.anchor).as_posix()
                    )
                )
        if entry is not None and entry.control is not None:
            native._validate_shared_head(entry.control)
        held.enter_context(_hold_material_references(prepared, root))
        validate_command(prepared, root, distribution, command)
        yield entry


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
    rows["management.json"] = captured["management"]
    inventory = {
        name: {"sha256": digest(raw), "size": len(raw)} for name, raw in rows.items()
    }
    inventory.update(
        {
            "runtime/" + name: {"sha256": row["sha256"], "size": row["size"]}
            for name, row in closure.items()
        }
    )
    destinations = [
        (destination / name).relative_to(root).as_posix()
        for name in (*inventory, "bundle.json")
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
    for name, row in closure.items():
        target = destination / "runtime" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        relative_target = target.relative_to(root).as_posix()
        with _safe_material_file(root, name) as source:
            if target.exists():
                with _safe_material_file(root, relative_target) as existing:
                    _stream_material(existing, row)
            else:
                with _safe_material_file(root, relative_target, create=True) as output:
                    _stream_material(source, row, output)
                    output.flush()
                    os.fsync(output.fileno())
    publish(destination, "bundle.json", canonical(inventory))
    return {"bundle_sha256": digest(canonical(inventory)), "files": len(inventory)}


def execute(prepared: dict[str, Any], root: Path) -> tuple[str, bytes]:
    with _hold_material_references(prepared, root):
        job, captured = capture_job(prepared, root)
        spec, _ = management(prepared, root, captured)
        operation = job["operation"]
        native = _captured_module(
            "pf_native_control", captured["native"], str(root / "accepted-native.py")
        )
        summary_archive = qualify_archive(
            captured["archive"], captured["manifest"], native
        )
        if operation == "qualify-archive":
            summary = summary_archive
        elif operation == "construct-management":
            summary = construct_management(prepared, root, captured)
        else:
            # Captured management code is independent of inhibited target imports.
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
