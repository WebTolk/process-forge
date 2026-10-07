"""Explicit entry migration with preconditions, private journals and safe rollback.

Each replacement is atomic, the set of replacements is not. The OS lock serializes
this service; it is not a sandbox against a hostile concurrent filesystem owner.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
import os
from pathlib import Path, PurePosixPath
import re
import stat
import uuid

from processforge_platforms.file_security import FileReplacementError, native_file_security

from .contract import (Contract, EntryError, block_span, decode_json, digest, encoded,
                          load_contract, project_content, text_bytes)


TARGETS = ("AGENTS.md", ".pf/AGENTS.md", ".pf/agent-entry.json")
START_TARGETS = (".pf/START_AGENT_HERE.md",)
ADAPTER_TARGETS = (("CLAUDE.md",), ("GEMINI.md",))
PLACEMENT_TARGETS = (TARGETS, START_TARGETS, *ADAPTER_TARGETS)
JOURNALS = ".pf/runtime/agent-entry-transactions"
MAX_FILE = 1048576
MAX_JOURNAL = 12 * MAX_FILE


def root_path(value: Path) -> Path:
    root = value.expanduser().absolute()
    for path in (*reversed(root.parents), root):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise EntryError("unsupported_path")
    if not root.is_dir():
        raise EntryError("project_root_missing")
    return root


def safe_path(root: Path, relative: str, *, writable: bool = False) -> Path:
    if (not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative
            or any(ord(char) < 32 for char in relative)
            or relative.startswith("/") or any(p in {"", ".", ".."} or p.endswith((".", " "))
                                                for p in relative.split("/"))):
        raise EntryError("unsupported_path")
    root_path(root)
    parts = PurePosixPath(relative).parts
    path = root
    for index, part in enumerate(parts):
        if path.exists():
            if not path.is_dir():
                raise EntryError("unsupported_path", relative)
            matches = [p.name for p in path.iterdir() if p.name.casefold() == part.casefold()]
            if matches and matches != [part]:
                raise EntryError("case_collision", relative)
        path = path / part
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        attrs = getattr(info, "st_file_attributes", 0)
        if stat.S_ISLNK(info.st_mode) or attrs & 0x400:
            raise EntryError("unsupported_path", relative)
        if index < len(parts) - 1:
            if not stat.S_ISDIR(info.st_mode):
                raise EntryError("unsupported_path", relative)
        elif not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)) or (
                stat.S_ISREG(info.st_mode) and info.st_nlink != 1):
            raise EntryError("unsupported_path", relative)
        if writable and not info.st_mode & stat.S_IWUSR:
            raise EntryError("read_only", relative)
    return path


def _acl(path: Path) -> bytes:
    try:
        descriptor = native_file_security().descriptor(path)
    except OSError:
        raise EntryError("unsupported_acl") from None
    if descriptor is None:
        raise EntryError("unsupported_acl")
    return descriptor


def _set_acl(path: Path, raw: bytes):
    try:
        native_file_security().restore(path, raw)
    except OSError:
        raise EntryError("unsupported_acl") from None


def security(path: Path) -> str:
    """Precondition includes owner/group/DACL; failure does not relax the check."""
    try:
        return native_file_security().fingerprint(path)
    except OSError:
        raise EntryError("unsupported_acl") from None


def read_file(root: Path, name: str, *, maximum: int = MAX_FILE, writable: bool = False):
    path = safe_path(root, name, writable=writable)
    if not path.exists():
        return None, {"sha256": None}
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > maximum or stat.S_IMODE(info.st_mode) & 0o7000:
        raise EntryError("unsupported_file", name)
    if writable and os.name != "nt":
        if info.st_uid != os.getuid() or info.st_gid != os.getgid():
            raise EntryError("unsupported_acl", name)
        if hasattr(os, "listxattr") and "system.posix_acl_access" in os.listxattr(path, follow_symlinks=False):
            raise EntryError("unsupported_acl", name)
    if os.name == "nt":
        from ..egress.windows import read_source
        from ..egress.contracts import EgressError
        try:
            raw = read_source(path, maximum)
        except EgressError:
            raise EntryError("source_changed", name) from None
    else:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino, opened.st_nlink) != (info.st_dev, info.st_ino, 1):
                raise EntryError("source_changed", name)
            raw = stream.read(maximum + 1)
    after = safe_path(root, name).stat()
    if (len(raw) > maximum or (info.st_ino, info.st_size, info.st_mtime_ns) !=
            (after.st_ino, after.st_size, after.st_mtime_ns)):
        raise EntryError("source_changed", name)
    return raw, {"sha256": digest(raw), "bytes": len(raw), "identity": [info.st_dev, info.st_ino],
                 "mode": stat.S_IMODE(info.st_mode), "security": security(path)}


def project_identity(root: Path) -> str:
    info = root.stat()
    return digest(encoded([os.path.normcase(str(root)), info.st_dev, info.st_ino]))


def manifest(contract: Contract) -> dict:
    return {"schema_version": 1, "kind": "pf.agent-entry", "contract_version": contract.version,
            "contract_sha256": contract.sha256, "projections": list(TARGETS[:2])}


def policy_input(value) -> list:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 32:
        raise EntryError("budget_policy_invalid")
    keys = {"id", "unit", "scope", "selection", "limit", "overflow", "source", "accounting_phase"}
    result = []
    ids = set()
    for row in value:
        if (not isinstance(row, dict) or set(row) != keys or not isinstance(row["id"], str)
                or not re.fullmatch(r"[a-z0-9-]{1,64}", row["id"]) or row["id"] in ids
                or any(not isinstance(row[k], str) for k in ("unit", "scope", "overflow", "source", "accounting_phase"))
                or row["unit"] not in {"utf8_bytes", "unicode_scalars", "utf16_code_units", "tokens"}
                or row["scope"] not in {"file", "chain"} or row["overflow"] not in {"truncate", "reject", "warn"}
                or row["source"] not in {"explicit", "default", "unknown"}
                or row["accounting_phase"] not in {"raw_concat", "unknown"}
                or not isinstance(row["selection"], list) or not 1 <= len(row["selection"]) <= 64
                or any(not isinstance(p, str) or not p for p in row["selection"])
                or (row["limit"] is not None and (type(row["limit"]) is not int or not 0 <= row["limit"] <= 2**40))):
            raise EntryError("budget_policy_invalid")
        ids.add(row["id"])
        result.append(dict(row, selection=list(row["selection"])))
    return result


def measure(raw: bytes, unit: str) -> int:
    if unit == "utf8_bytes":
        return len(raw)
    text = raw.decode("utf-8")
    return len(text.encode("utf-16-le")) // 2 if unit == "utf16_code_units" else len(text)


def budgets(root: Path, proposed: dict[str, bytes], policies: list, contract: Contract):
    cache, inputs, results, blockers = dict(proposed), {}, [], []
    for policy in policies:
        counts, cumulative, found_k = [], 0, False
        known = policy["limit"] is not None and policy["unit"] != "tokens" and policy["accounting_phase"] == "raw_concat"
        all_complete, k_complete = True, True
        for name in policy["selection"]:
            if name not in cache:
                if len(cache) >= 67:
                    raise EntryError("budget_input_limit")
                raw, pre = read_file(root, name)
                if raw is None:
                    raise EntryError("budget_input_missing", name)
                text_bytes(raw)
                cache[name], inputs[name] = raw, pre
            raw = cache[name]
            span = block_span(raw, contract)
            size = measure(raw, policy["unit"]) if policy["unit"] != "tokens" else None
            offset = cumulative if policy["scope"] == "chain" else 0
            full = None if not known else offset + size <= policy["limit"] or policy["overflow"] == "warn"
            end = measure(raw[:span[1]], policy["unit"]) if span and size is not None else None
            delivered = None if not known or not span else offset + end <= policy["limit"] or policy["overflow"] == "warn"
            if known and policy["overflow"] == "reject" and not full:
                delivered = False if span else None
            found_k |= bool(span)
            all_complete &= full is not False
            k_complete &= delivered is not False
            counts.append({"path": name, "size": size, "chain_offset": offset, "k_end": end,
                           "k_fully_delivered": delivered, "required_complete": full})
            cumulative += size or 0
        if not found_k:
            blockers.append("entry_contract_not_selected")
        if not k_complete:
            blockers.append("entry_contract_would_truncate")
        if not all_complete:
            blockers.append("required_instructions_would_truncate")
        verified = known and policy["source"] == "explicit" and found_k
        results.append({"id": policy["id"], "unit": policy["unit"], "scope": policy["scope"],
                        "status": "accounted" if verified else "budget_unverified", "files": counts,
                        "total": cumulative if policy["unit"] != "tokens" else None,
                        "k_fully_delivered": k_complete if verified else None,
                        "all_required_complete": all_complete if verified else None,
                        "warning": bool(known and policy["overflow"] == "warn" and any(
                            (x["chain_offset"] + x["size"]) > policy["limit"] for x in counts))})
    status = "accounted" if results and all(r["status"] == "accounted" for r in results) else "budget_unverified"
    return {"status": status, "policies": results}, inputs, sorted(set(blockers))


def _read_journal(root: Path, transaction: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{32}", transaction):
        raise EntryError("transaction_id_invalid")
    raw, _ = read_file(root, f"{JOURNALS}/{transaction}.json", maximum=MAX_JOURNAL)
    if raw is None:
        raise EntryError("transaction_missing")
    envelope = decode_json(raw, MAX_JOURNAL)
    if (not isinstance(envelope, dict) or set(envelope) != {"payload", "sha256"}
            or digest(encoded(envelope["payload"])) != envelope["sha256"]):
        raise EntryError("journal_invalid")
    value = envelope["payload"]
    if (not isinstance(value, dict) or set(value) != {"schema_version", "transaction", "project", "state", "files"}
            or type(value["schema_version"]) is not int or value["schema_version"] != 1 or value["transaction"] != transaction
            or value["project"] != project_identity(root)
            or not isinstance(value["state"], str) or value["state"] not in {"prepared", "committed", "rolling_back", "rolled_back"}
            or not isinstance(value["files"], list) or any(not isinstance(x, dict) for x in value["files"])
            or tuple(x.get("path") for x in value["files"]) not in PLACEMENT_TARGETS):
        raise EntryError("journal_invalid")
    for row in value["files"]:
        if (set(row) != {"path", "before", "after", "before_sha256", "after_sha256", "mode", "before_security", "after_security", "transient_security", "acl"}
                or type(row["mode"]) is not int or not 0 <= row["mode"] <= 0o777
                or any(row[k] is not None and not isinstance(row[k], str) for k in ("before_security", "after_security", "transient_security", "acl"))):
            raise EntryError("journal_invalid")
        if row["acl"] is not None:
            try:
                acl = base64.b64decode(row["acl"], validate=True)
            except ValueError:
                raise EntryError("journal_invalid") from None
            if not 1 <= len(acl) <= 65536 or digest(acl) != row["before_security"]:
                raise EntryError("journal_invalid")
        for side in ("before", "after"):
            try:
                data = None if row[side] is None else base64.b64decode(row[side], validate=True)
            except (ValueError, TypeError):
                raise EntryError("journal_invalid") from None
            if (side == "after" and data is None or data is not None and len(data) > MAX_FILE
                    or (digest(data) if data is not None else None) != row[side + "_sha256"]):
                raise EntryError("journal_invalid")
    return value


def pending(root: Path) -> list[str]:
    folder = safe_path(root, JOURNALS)
    if not folder.exists():
        return []
    if not folder.is_dir():
        raise EntryError("unsupported_path", JOURNALS)
    names = sorted(p.stem for p in folder.glob("*.json"))
    if len(names) > 256:
        raise EntryError("journal_inventory_limit")
    return [name for name in names if _read_journal(root, name)["state"] in {"prepared", "rolling_back"}]


def _plan(root: Path, contract: Contract, policies: list):
    root = root_path(root)
    previous, proposed, preconditions, rows = {}, {}, {}, []
    for name in TARGETS:
        raw, pre = read_file(root, name, writable=True)
        previous[name], preconditions[name] = raw, pre
    for name in TARGETS[:2]:
        try:
            after, action = project_content(previous[name], contract, hidden=name.startswith(".pf/"))
        except EntryError as exc:
            raise EntryError(exc.reason, name) from None
        if len(after) > MAX_FILE:
            raise EntryError("output_too_large", name)
        proposed[name] = after
        span = block_span(after, contract)
        rows.append({"path": name, "action": action, "before_sha256": preconditions[name]["sha256"],
                     "after_sha256": digest(after), "whole_file_bytes": len(after),
                     "k_start": span[0], "k_end": span[1], "placed_k_bytes": span[1] - span[0]})
    wanted = manifest(contract)
    raw = previous[TARGETS[2]]
    if raw is not None:
        old = decode_json(raw)
        if (not isinstance(old, dict) or set(old) != set(wanted) or type(old["schema_version"]) is not int or old["schema_version"] != 1
                or old["kind"] != wanted["kind"] or old["projections"] != wanted["projections"]
                or (old["contract_version"], old["contract_sha256"]) not in contract.known):
            raise EntryError("entry_manifest_conflict", TARGETS[2])
        # A known manifest cannot legitimize a missing or independently edited K.
        for name in TARGETS[:2]:
            span = block_span(previous[name] or b"", contract)
            if span is None:
                raise EntryError("entry_manifest_conflict", name)
    proposed[TARGETS[2]] = encoded(wanted)
    rows.append({"path": TARGETS[2], "action": "unchanged" if raw == proposed[TARGETS[2]] else "write_manifest",
                 "before_sha256": preconditions[TARGETS[2]]["sha256"], "after_sha256": digest(proposed[TARGETS[2]])})
    accounting, inputs, blockers = budgets(root, proposed, policies, contract)
    interrupted = pending(root)
    if interrupted:
        blockers.append("entry_transaction_incomplete")
    plan = {"schema_version": 1, "kind": "pf.agent-entry.plan", "project": project_identity(root),
            "source_digest": contract.source_digest, "contract_version": contract.version,
            "contract_sha256": contract.sha256, "canonical_k_bytes": len(contract.raw),
            "generated_contract": contract.raw.decode("utf-8"),
            "new_hidden_extension": contract.extended.decode("utf-8") if previous[TARGETS[1]] is None else None,
            "preconditions": preconditions, "files": rows, "budget_policy": policies,
            "budget_inputs": inputs, "budget": accounting, "blockers": sorted(set(blockers)),
            "pending_transactions": interrupted,
            "status": "conflict" if blockers else "current" if previous == proposed else "planned"}
    plan["digest"] = digest(encoded(plan))
    return plan, previous, proposed


def plan_entry(project: Path, *, source: Path | None = None, budget_policy=None) -> dict:
    contract = load_contract(source) if source is not None else load_contract()
    return _plan(root_path(project), contract, policy_input(budget_policy))[0]


def _start_plan(root: Path):
    from .start_prompt import load_start_source, project_start_content
    root = root_path(root)
    generated, source_digest, legacy = load_start_source()
    name = START_TARGETS[0]
    raw, pre = read_file(root, name, writable=True)
    after, action = project_start_content(raw, generated, legacy)
    if len(after) > MAX_FILE:
        raise EntryError("output_too_large", name)
    interrupted = pending(root)
    blockers = ["entry_transaction_incomplete"] if interrupted else []
    plan = {"schema_version": 1, "kind": "pf.agent-start-prompt.plan", "project": project_identity(root),
            "source_digest": source_digest, "generated_prompt": generated,
            "preconditions": {name: pre},
            "files": [{"path": name, "action": action, "before_sha256": pre["sha256"], "after_sha256": digest(after)}],
            "budget_inputs": {}, "budget": {"status": "not_applicable", "reason": "compatibility_prompt_not_k"},
            "blockers": blockers, "pending_transactions": interrupted,
            "status": "conflict" if blockers else "current" if raw == after else "planned"}
    plan["digest"] = digest(encoded(plan))
    return plan, {name: raw}, {name: after}


def plan_start_prompt(project: Path) -> dict:
    return _start_plan(root_path(project))[0]


def apply_start_prompt(project: Path, supplied: dict, *, apply: bool = False, _fault=None) -> dict:
    from .start_prompt import load_start_source
    return _apply_placement(project, supplied, apply=apply, targets=START_TARGETS, planner=_start_plan,
                            source_guard=lambda: load_start_source()[1], _fault=_fault)


def check_entry(project: Path, **kwargs) -> dict:
    plan = plan_entry(project, **kwargs)
    return {"schema_version": 1, "kind": "pf.agent-entry.check", "status": plan["status"],
            "entry": "current" if plan["status"] == "current" else "legacy_or_unmigrated",
            "budget": plan["budget"], "blockers": plan["blockers"], "plan_digest": plan["digest"],
            "files": plan["files"], "pending_transactions": plan["pending_transactions"]}


def _directory(root: Path, name: str, *, private: bool = False):
    path = safe_path(root, name, writable=True)
    if private and os.name == "nt":
        from ..egress.windows import private_directory
        from ..egress.contracts import EgressError
        try:
            private_directory(path)
        except EgressError:
            raise EntryError("private_acl_unavailable", name) from None
    else:
        path.mkdir(mode=0o700 if private else 0o755, exist_ok=True)
        if private and (stat.S_IMODE(path.stat().st_mode) & 0o077 or path.stat().st_uid != os.getuid()):
            raise EntryError("private_acl_unavailable", name)
    safe_path(root, name, writable=True)
    return path


@contextmanager
def entry_lock(root: Path):
    for name in (".pf", ".pf/runtime"):
        _directory(root, name)
    _directory(root, JOURNALS, private=True)
    path = safe_path(root, f"{JOURNALS}/writer.lock", writable=True)
    # Keep the inode: deleting a lock file can allow two independent OS locks.
    with path.open("a+b") as stream:
        if stream.seek(0, 2) == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise EntryError("entry_writer_busy") from None
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _durable_file(path: Path, raw: bytes):
    with path.open("xb") as stream:
        if os.name != "nt":
            os.fchmod(stream.fileno(), 0o600)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _sync_dir(path: Path):
    if os.name != "nt":
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _journal(root: Path, value: dict):
    name = f"{JOURNALS}/{value['transaction']}.json"
    temporary = safe_path(root, f"{JOURNALS}/{uuid.uuid4().hex}.part", writable=True)
    _durable_file(temporary, encoded({"payload": value, "sha256": digest(encoded(value))}))
    os.replace(temporary, safe_path(root, name, writable=True))
    _sync_dir(temporary.parent)


def _stage(root: Path, transaction: str, raw: bytes) -> Path:
    _directory(root, ".pf/tmp")
    directory = _directory(root, f".pf/tmp/agent-entry-{transaction}", private=True)
    path = safe_path(root, directory.relative_to(root).as_posix() + f"/{uuid.uuid4().hex}.stage", writable=True)
    _durable_file(path, raw)
    return path


def _replace(root: Path, name: str, staged: Path, mode: int, *, acl=None, fault=None, transaction=""):
    target = safe_path(root, name, writable=True)
    safe_path(root, staged.relative_to(root).as_posix(), writable=True)
    try:
        native_file_security().replace(target, staged, mode)
    except FileReplacementError:
        raise EntryError("replacement_failed", name) from None
    if fault:
        fault("replaced_data:" + name, transaction)
    if acl is not None:
        # Some filesystems re-inherit the staging parent's ACL during replacement.
        # This metadata step is journaled separately from the atomic data replace.
        _set_acl(safe_path(root, name, writable=True), base64.b64decode(acl, validate=True))
    _sync_dir(target.parent)


def _expect(root: Path, name: str, expected: dict):
    _, current = read_file(root, name, writable=True)
    if current != expected:
        raise EntryError("precondition_changed", name)


def _replacement_security(root: Path, transaction: str, name: str, acl: str) -> str:
    """Qualify the filesystem's ACL merge on empty private files before writes."""
    second = _stage(root, transaction, b"")
    directory_name = f".pf/tmp/agent-entry-{transaction}/probe-{uuid.uuid4().hex}"
    directory = _directory(root, directory_name)
    target_parent = safe_path(root, name).parent
    _set_acl(directory, _acl(target_parent))
    first = safe_path(root, directory_name + "/probe", writable=True)
    _durable_file(first, b"")
    descriptor = base64.b64decode(acl, validate=True)
    _set_acl(first, descriptor)
    _set_acl(second, descriptor)
    name = first.relative_to(root).as_posix()
    _replace(root, name, second, 0o600)
    result = security(first)
    safe_path(root, name, writable=True).unlink()
    safe_path(root, directory_name, writable=True).rmdir()
    return result


def _states(root: Path, journal: dict) -> list:
    result = []
    for row in journal["files"]:
        try:
            _, state = read_file(root, row["path"], writable=True)
            h = state["sha256"]
            actual = "before" if h == row["before_sha256"] else "after" if h == row["after_sha256"] else "conflict"
            if actual != "conflict" and h is not None:
                permitted = {row[actual + "_security"]}
                if journal["state"] in {"prepared", "rolling_back"}:
                    permitted.add(row["transient_security"])
                if state["security"] not in permitted:
                    actual = "conflict"
        except (EntryError, OSError):
            actual = "conflict"
        result.append({"path": row["path"], "state": actual})
    return result


def apply_entry(project: Path, supplied: dict, *, apply: bool = False, source: Path | None = None, _fault=None) -> dict:
    def contract():
        return load_contract(source) if source is not None else load_contract()
    return _apply_placement(project, supplied, apply=apply, targets=TARGETS,
                            planner=lambda root: _plan(root, contract(), policy_input(supplied.get("budget_policy"))),
                            source_guard=lambda: contract().source_digest, _fault=_fault)


def _apply_placement(project: Path, supplied: dict, *, apply: bool, targets: tuple,
                     planner, source_guard, _fault=None) -> dict:
    # Only bounded placement services can choose a fixed target set. Journals use the
    # same whitelist; arbitrary file placement is deliberately unsupported.
    if targets not in PLACEMENT_TARGETS:
        raise EntryError("plan_invalid")
    if not apply:
        raise EntryError("explicit_apply_required")
    if not isinstance(supplied, dict) or not isinstance(supplied.get("digest"), str):
        raise EntryError("plan_invalid")
    root = root_path(project)
    # Reject altered plan fields, as well as a stale digest, before creating a lock.
    original = {k: v for k, v in supplied.items() if k != "digest"}
    if digest(encoded(original)) != supplied["digest"]:
        raise EntryError("plan_invalid")
    initial, _, _ = planner(root)
    if initial != supplied:
        raise EntryError("plan_stale")
    if initial["blockers"]:
        raise EntryError(initial["blockers"][0])
    if initial["status"] == "current":
        return {"action": "unchanged", "budget": initial["budget"]}
    with entry_lock(root):
        plan, before, after = planner(root)
        if plan != supplied:
            raise EntryError("plan_stale")
        tx = uuid.uuid4().hex
        journal = {"schema_version": 1, "transaction": tx, "project": project_identity(root), "state": "prepared",
                   "files": [{"path": name, "before": base64.b64encode(before[name]).decode() if before[name] is not None else None,
                              "after": base64.b64encode(after[name]).decode(), "before_sha256": plan["preconditions"][name]["sha256"],
                              "after_sha256": digest(after[name]), "mode": plan["preconditions"][name].get("mode", 0o644),
                              "before_security": plan["preconditions"][name].get("security"),
                              "after_security": plan["preconditions"][name].get("security"), "transient_security": None,
                              "acl": base64.b64encode(_acl(root / name)).decode() if os.name == "nt" and before[name] is not None else None} for name in targets]}
        _journal(root, journal)
        try:
            staged = {name: _stage(root, tx, after[name]) for name in targets if before[name] != after[name]}
            for row in journal["files"]:
                if row["path"] in staged:
                    row["transient_security"] = security(staged[row["path"]])
                    if row["acl"] is not None:
                        row["transient_security"] = _replacement_security(root, tx, row["path"], row["acl"])
                        _set_acl(staged[row["path"]], base64.b64decode(row["acl"], validate=True))
                if row["before"] is None:
                    row["after_security"] = security(staged[row["path"]]) if os.name == "nt" else str(row["mode"])
            _journal(root, journal)
            if _fault:
                _fault("staged", tx)
            if source_guard() != plan["source_digest"]:
                raise EntryError("contract_source_changed")
            for name, expected in plan["budget_inputs"].items():
                _expect(root, name, expected)
            for name in targets:
                _expect(root, name, plan["preconditions"][name])
            for name in targets:  # Entry manifest is last; START has one target.
                if name not in staged:
                    continue
                _expect(root, name, plan["preconditions"][name])
                staged_raw, _ = read_file(root, staged[name].relative_to(root).as_posix())
                if staged_raw != after[name]:
                    raise EntryError("staging_changed", name)
                row = next(row for row in journal["files"] if row["path"] == name)
                _replace(root, name, staged[name], row["mode"], acl=row["acl"], fault=_fault, transaction=tx)
                if _fault:
                    _fault("replaced:" + name, tx)
                raw, state = read_file(root, name, writable=True)
                if raw != after[name] or (before[name] is not None and state["security"] != plan["preconditions"][name]["security"]):
                    raise EntryError("replacement_verification_failed", name)
            for name in targets:
                raw, state = read_file(root, name, writable=True)
                row = next(row for row in journal["files"] if row["path"] == name)
                if raw != after[name] or state["security"] != row["after_security"]:
                    raise EntryError("replacement_verification_failed", name)
            for name, expected in plan["budget_inputs"].items():
                _expect(root, name, expected)
            if source_guard() != plan["source_digest"]:
                raise EntryError("contract_source_changed")
            journal["state"] = "committed"
            _journal(root, journal)
            return {"action": "applied", "transaction": tx, "budget": plan["budget"], "files": _states(root, journal)}
        except (EntryError, OSError) as exc:
            return {"action": "incomplete", "transaction": tx, "reason": exc.reason if isinstance(exc, EntryError) else "storage_error",
                    "files": _states(root, journal), "remediation": "rollback_transaction"}


def rollback_entry(project: Path, transaction: str, *, apply: bool = False, _fault=None) -> dict:
    if not apply:
        raise EntryError("explicit_apply_required")
    root = root_path(project)
    journal = _read_journal(root, transaction)
    # All-file preflight precedes both state changes and file restoration.
    states = _states(root, journal)
    if any(row["state"] == "conflict" for row in states):
        raise EntryError("rollback_conflict")
    with entry_lock(root):
        journal = _read_journal(root, transaction)
        states = _states(root, journal)
        if any(row["state"] == "conflict" for row in states):
            raise EntryError("rollback_conflict")
        if journal["state"] == "rolled_back":
            if any(row["state"] != "before" for row in states):
                raise EntryError("rollback_conflict")
            return {"action": "unchanged", "transaction": transaction}
        journal["state"] = "rolling_back"
        _journal(root, journal)
        try:
            for row in journal["files"]:
                name = row["path"]
                raw, pre = read_file(root, name, writable=True)
                if pre["sha256"] == row["before_sha256"]:
                    if raw is not None and pre["security"] != row["before_security"]:
                        if row["acl"] is None:
                            raise EntryError("rollback_conflict", name)
                        _expect(root, name, pre)
                        _set_acl(safe_path(root, name, writable=True), base64.b64decode(row["acl"], validate=True))
                    continue
                if pre["sha256"] != row["after_sha256"]:
                    raise EntryError("rollback_conflict", name)
                if row["before"] is None:
                    _expect(root, name, pre)
                    safe_path(root, name, writable=True).unlink()
                    _sync_dir((root / name).parent)
                else:
                    staged = _stage(root, transaction, base64.b64decode(row["before"], validate=True))
                    row["transient_security"] = security(staged)
                    if row["acl"] is not None:
                        row["transient_security"] = _replacement_security(root, transaction, row["path"], row["acl"])
                        _set_acl(staged, base64.b64decode(row["acl"], validate=True))
                    _journal(root, journal)
                    _expect(root, name, pre)
                    _replace(root, name, staged, row["mode"], acl=row["acl"], fault=_fault, transaction=transaction)
                if _fault:
                    _fault("restored:" + name, transaction)
            if any(row["state"] != "before" for row in _states(root, journal)):
                raise EntryError("rollback_conflict")
            for row in journal["files"]:
                raw, state = read_file(root, row["path"], writable=True)
                if raw is not None and state["security"] != row["before_security"]:
                    raise EntryError("rollback_conflict", row["path"])
            journal["state"] = "rolled_back"
            _journal(root, journal)
            return {"action": "rolled_back", "transaction": transaction}
        except (EntryError, OSError) as exc:
            return {"action": "incomplete", "transaction": transaction, "reason": exc.reason if isinstance(exc, EntryError) else "storage_error",
                    "files": _states(root, journal), "remediation": "rollback_transaction"}
