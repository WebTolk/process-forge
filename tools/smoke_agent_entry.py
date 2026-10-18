#!/usr/bin/env python3
"""Source qualification: ownership, budgets, real files, crash and OS lock.

No client discovery, delivered prompt, model behavior or installed Core claim.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import runpy
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from processforge_core.agent_entry.contract import (BOM, EntryError, block_span, decode_json, digest, encoded, load_contract)
from processforge_core.agent_entry.migration import (TARGETS, JOURNALS, apply_entry, check_entry,
    entry_lock, manifest, measure, pending, plan_entry, rollback_entry, security)


def tree(root):
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def targets(root):
    return {name: (root / name).read_bytes() if (root / name).exists() else None for name in TARGETS}


def reject(reason, call):
    try:
        call()
    except EntryError as exc:
        assert exc.reason == reason, (reason, exc.reason)
    else:
        raise AssertionError("expected " + reason)


def budget(limit, *, selection=None, unit="utf8_bytes", scope="chain", overflow="truncate", source="explicit"):
    return [{"id": "fixture", "unit": unit, "scope": scope, "selection": selection or ["AGENTS.md"],
             "limit": limit, "overflow": overflow, "source": source, "accounting_phase": "raw_concat"}]


def source_checks(base):
    contract = load_contract()
    assert len(contract.raw) <= 4096 and contract.sha256 == digest(contract.raw)
    assert contract.render(extended=True) == (ROOT / "templates/project-agents-template.md").read_bytes()
    assert block_span(contract.raw, contract) == (0, len(contract.raw))
    source = base / "source"
    (source / "templates").mkdir(parents=True)
    files = ["agent-entry-contract.md", "agent-entry-contract.json", "project-agents-template.md"]
    for name in files:
        shutil.copyfile(ROOT / "templates" / name, source / "templates" / name)
    raw_path = source / "templates/agent-entry-contract.md"
    original = raw_path.read_bytes()
    for raw, reason in [(BOM + original, "contract_source_invalid"),
                        (original.replace(b"\n", b"\r\n"), "contract_source_invalid"),
                        (original.replace(b"1. Locate", b"9. Locate"), "contract_source_invalid"),
                        (original.replace(b"Locate", b"LOCATE"), "contract_hash_mismatch"),
                        (original.replace(contract.version.encode(), b"2.0.0"), "contract_source_invalid"),
                        (original.replace(b"\n1. ", b"\n" + b"x" * 4096 + b"\n1. "), "contract_source_invalid")]:
        raw_path.write_bytes(raw)
        reject(reason, lambda: load_contract(source))
    raw_path.write_bytes(original)
    template = source / "templates/project-agents-template.md"
    template.write_bytes(b"Read hidden instructions instead.\n")
    reject("derived_template_stale", lambda: load_contract(source))
    shutil.copyfile(ROOT / "templates/project-agents-template.md", template)
    reject("duplicate_json_key", lambda: decode_json(b'{"schema_version":1,"schema_version":2}'))
    meta_path = source / "templates/agent-entry-contract.json"
    original_meta = meta_path.read_bytes()
    meta = json.loads(original_meta)
    padded = original.replace(b"<!-- PF:ENTRY:END -->", b"x" * (4096 - len(original)) + b"\n<!-- PF:ENTRY:END -->")
    padded = padded.replace(b"x\n<!--", b"\n<!--", 1)  # exact 4096 including final newline
    assert len(padded) == 4096
    meta["sha256"] = digest(padded)
    meta["known_blocks"] = [{"version": meta["contract_version"], "sha256": digest(padded)}]
    raw_path.write_bytes(padded)
    meta_path.write_bytes(encoded(meta))
    template.write_bytes(padded + b"\n" + contract.extended)
    bounded = load_contract(source)
    assert len(bounded.raw) == 4096
    reject("placed_contract_too_large", lambda: block_span(padded.replace(b"\n", b"\r\n"), bounded))
    raw_path.write_bytes(original)
    meta_path.write_bytes(original_meta)
    shutil.copyfile(ROOT / "templates/project-agents-template.md", template)
    return contract, source


# A recognized historical prefix is fixture data, independent of checkout entry files.
LEGACY_HIDDEN_PREFIX = """# AGENTS.md

## Mission

Use ProcessForge as a file-first process system. Work through assignments, execution contexts, artifacts, reviews, handoffs, logs, and ADRs.

## Boot Sequence

1. Read this file.
2. Read `.pf/process-forge.yaml`.
3. Call `pf.context` with the project root, or read the current snapshot only
   when MCP is unavailable.
4. Use `pf.search` for authorized project knowledge and `pf.resolve` before
   opening ProcessForge-managed resource roots.
5. Call `pf.work.start` with the objective when work becomes substantive. If it
   returns `process_choice_required`, choose an offered process and call it
   again with `process_id`; do not infer from `default` when multiple processes
   are allowed.
6. Call `pf.work.state` and read the selected assignment and immutable
   Execution Context Package.
7. Check allowed and forbidden files before editing.
8. Satisfy the current stage obligations, then call `pf.work.transition` with
   a declared outcome and evidence. Never choose `next_stage` directly.
9. Repeat state, work, and transition until PF returns `action: run_completed`.

## Core Rules

- File-only mode is the default.
- One file scope has one responsible writer.
- Assignments define the work boundary.
- Do not edit files outside the assignment scope without a handoff.
- Approved artifacts are protected.
- Execution Context Packages are immutable snapshots.
- Process versions are immutable.
- ProcessForge selects the initial stage and every next stage from the pinned
  Process definition. Agents provide outcomes and evidence, not stage ids.
- Runner and backend support are optional future modes, not requirements.
- Public product files must not include private paths, secrets, machine names, or temporary private notes.
- Use stable machine-readable ids for statuses, processes, artifacts, assignments, templates, and packages.
- Create every repository-local temporary directory under `.pf/tmp/`; never create temporary worker, debug, staging, or scratch directories at the repository root.
- In particular, do not create root directories named `.pf-worker-shell-*` or similar runner sandboxes. Clean `.pf/tmp/` outputs after use unless they are declared durable evidence.
- System temporary directories are allowed only for isolated tests that never write a temporary directory into the repository.
- During ordinary project work, do not install, start, restart, or repair PF
  Runtime, MCP, host hooks, or Agent Ledger. Use available PF tools. If PF
  returns an operator-level infrastructure blocker, report it to the operator.
- Current `pf.context`/snapshot state outranks historical generated reports.
  Do not treat a report marked `stale` or `historical` as current truth.
- A completed Work can offer a compact fresh-session handoff through
  `pf.context`; it is advisory and must not cause Runtime, MCP, Ledger, or
  external-session lifecycle actions.
- `run-create`, `task-create`, `task-complete`, and `run-complete` are
  compatibility and diagnostic commands, not the ordinary agent workflow.

""".encode("utf-8")


def ownership_checks(base, contract):
    root = base / "ownership"
    (root / ".pf").mkdir(parents=True)
    prefix, suffix = BOM + "Пользователь 😀\r\n".encode(), b"\r\n## Private notes\r\nKEEP EXACT\r\n"
    root_before = prefix + contract.raw.replace(b"\n", b"\r\n") + suffix
    assert any(count == 53 and expected == digest(LEGACY_HIDDEN_PREFIX)
               for count, expected, _heading in contract.legacy), "legacy fixture no longer recognized"
    hidden_before = LEGACY_HIDDEN_PREFIX + b"## Standard Statuses\nKEEP LEGACY SUFFIX EXACT\n"
    (root / "AGENTS.md").write_bytes(root_before)
    (root / ".pf/AGENTS.md").write_bytes(hidden_before)
    original = targets(root)
    before = tree(root)
    plan = plan_entry(root)
    check_entry(root)
    assert tree(root) == before, "plan/check wrote files"
    assert "KEEP EXACT" not in json.dumps(plan), "public plan leaked surrounding text"
    acl_before = security(root / "AGENTS.md")
    receipt = apply_entry(root, plan, apply=True)
    assert receipt["action"] == "applied", receipt
    assert (root / "AGENTS.md").read_bytes() == root_before
    assert security(root / "AGENTS.md") == acl_before
    hidden = (root / ".pf/AGENTS.md").read_bytes()
    assert block_span(hidden, contract)
    heading = b"## Standard Statuses"
    assert hidden.split(heading, 1)[1] == hidden_before.split(heading, 1)[1]
    validator = runpy.run_path(str(ROOT / "tools/validate-process-forge-schemas.py"))["validate_against_schema"]
    validator(json.loads((root / ".pf/agent-entry.json").read_bytes()),
              json.loads((ROOT / "schemas/agent-entry.schema.json").read_bytes()), "entry fixture")
    repeated = plan_entry(root)
    assert repeated["status"] == "current"
    before = tree(root)
    assert apply_entry(root, repeated, apply=True)["action"] == "unchanged"
    assert tree(root) == before
    (root / "AGENTS.md").write_bytes(root_before + b"later edit")
    edited = tree(root)
    reject("rollback_conflict", lambda: rollback_entry(root, receipt["transaction"], apply=True))
    assert tree(root) == edited
    (root / "AGENTS.md").write_bytes(root_before)
    assert rollback_entry(root, receipt["transaction"], apply=True)["action"] == "rolled_back"
    assert targets(root) == original
    before = tree(root)
    assert rollback_entry(root, receipt["transaction"], apply=True)["action"] == "unchanged"
    assert tree(root) == before


def conflict_checks(base, contract, source):
    cases = [(contract.raw * 2, "managed_markers_invalid"),
             (contract.raw.replace(b"<!-- PF:ENTRY:END -->", b""), "managed_markers_invalid"),
             (contract.raw.replace(contract.version.encode(), b"9.0.0"), "managed_version_unknown"),
             (contract.raw.replace(b"Locate", b"Mutate"), "managed_content_changed"),
             (b"\xff\xfe", "unsupported_encoding"), (b"binary\x00", "binary_content")]
    for index, (raw, reason) in enumerate(cases):
        root = base / f"conflict-{index}"
        root.mkdir()
        (root / "AGENTS.md").write_bytes(raw)
        before = tree(root)
        reject(reason, lambda: plan_entry(root))
        assert tree(root) == before
    root = base / "custom-hidden"
    (root / ".pf").mkdir(parents=True)
    (root / ".pf/AGENTS.md").write_bytes(b"Private custom instructions\n")
    reject("legacy_hidden_unknown", lambda: plan_entry(root))
    root = base / "unknown-manifest"
    (root / ".pf").mkdir(parents=True)
    for name in TARGETS[:2]:
        (root / name).write_bytes(contract.raw)
    value = manifest(contract)
    value["schema_version"] = 2
    (root / TARGETS[2]).write_bytes(encoded(value))
    before = tree(root)
    reject("entry_manifest_conflict", lambda: plan_entry(root))
    assert tree(root) == before
    root = base / "stale"
    root.mkdir()
    (root / "AGENTS.md").write_bytes(b"before, no newline")
    plan = plan_entry(root)
    for path in ("../outside.md", "/outside.md", "drive:secret", "a\\b", "bad\x00name"):
        reject("unsupported_path", lambda: plan_entry(root, budget_policy=budget(9000, selection=["AGENTS.md", path])))
    bad = copy.deepcopy(plan)
    bad["files"][0]["action"] = "overwrite"
    reject("plan_invalid", lambda: apply_entry(root, bad, apply=True))
    reject("explicit_apply_required", lambda: apply_entry(root, plan))
    (root / "AGENTS.md").write_bytes(b"late user bytes")
    before = tree(root)
    reject("plan_stale", lambda: apply_entry(root, plan, apply=True))
    assert tree(root) == before
    plan = plan_entry(root, source=source)
    meta_path = source / "templates/agent-entry-contract.json"
    raw = meta_path.read_bytes()
    meta_path.write_bytes(raw + b"\n")
    reject("plan_stale", lambda: apply_entry(root, plan, apply=True, source=source))
    assert tree(root) == before
    meta_path.write_bytes(raw)
    root = base / "case"
    root.mkdir()
    (root / "agents.md").write_bytes(b"keep")
    reject("case_collision", lambda: plan_entry(root))
    root = base / "hardlink"
    root.mkdir()
    (root / "original.txt").write_bytes(b"keep")
    os.link(root / "original.txt", root / "AGENTS.md")
    reject("unsupported_path", lambda: plan_entry(root))
    root = base / "readonly"
    root.mkdir()
    path = root / "AGENTS.md"
    path.write_bytes(b"keep")
    path.chmod(stat.S_IREAD)
    try:
        reject("read_only", lambda: plan_entry(root))
    finally:
        path.chmod(stat.S_IREAD | stat.S_IWRITE)
    root = base / "redirect"
    root.mkdir()
    outside = base / "outside"
    outside.mkdir()
    if os.name == "nt":
        out = subprocess.run(["cmd", "/c", "mklink", "/J", str(root / ".pf"), str(outside)], capture_output=True)
        assert out.returncode == 0, "junction fixture unavailable"
        try:
            reject("unsupported_path", lambda: plan_entry(root))
            assert not list(outside.iterdir())
        finally:
            os.rmdir(root / ".pf")
    else:
        (root / ".pf").symlink_to(outside, target_is_directory=True)
        reject("unsupported_path", lambda: plan_entry(root))
        (root / ".pf").unlink()


def budget_checks(base, contract):
    root = base / "budgets"
    root.mkdir()
    path = root / "AGENTS.md"
    path.write_bytes(b"x" * (30 * 1024))
    plan = plan_entry(root, budget_policy=budget(32768))
    assert "entry_contract_would_truncate" in plan["blockers"]
    before = tree(root)
    reject("entry_contract_would_truncate", lambda: apply_entry(root, plan, apply=True))
    assert tree(root) == before
    path.write_bytes(contract.raw + b"x" * 32768)
    plan = plan_entry(root, budget_policy=budget(32768))
    row = plan["budget"]["policies"][0]
    assert row["k_fully_delivered"] and not row["all_required_complete"]
    assert plan["blockers"] == ["required_instructions_would_truncate"]
    path.write_bytes(contract.raw + b"x" * (20480 - len(contract.raw)))
    (root / "nested.md").write_bytes(b"y" * 20480)
    policy = budget(32768, selection=["AGENTS.md", "nested.md"])
    plan = plan_entry(root, budget_policy=policy)
    assert plan["budget"]["policies"][0]["total"] == 40960 and plan["blockers"]
    assert not plan_entry(root, budget_policy=budget(32768, selection=["AGENTS.md", "nested.md"], scope="file"))["blockers"]
    assert "entry_contract_would_truncate" in plan_entry(root, budget_policy=budget(22000, selection=["AGENTS.md", "AGENTS.md"]))["blockers"]
    assert "entry_contract_not_selected" in plan_entry(root, budget_policy=budget(32768, selection=["nested.md"]))["blockers"]
    path.write_bytes(contract.raw)
    for limit, blocks in [(len(contract.raw), False), (len(contract.raw) - 1, True), (0, True)]:
        assert bool(plan_entry(root, budget_policy=budget(limit))["blockers"]) == blocks
    for policy in [None, budget(None, source="unknown"), budget(32768, source="default"), budget(8192, unit="tokens")]:
        assert plan_entry(root, budget_policy=policy)["budget"]["status"] == "budget_unverified"
    plan = plan_entry(root, budget_policy=budget(0, overflow="warn"))
    assert not plan["blockers"] and plan["budget"]["policies"][0]["warning"]
    raw = "é😀".encode()
    assert [measure(raw, u) for u in ("utf8_bytes", "unicode_scalars", "utf16_code_units")] == [6, 2, 3]
    path.write_bytes(raw + b"\n")
    count = measure(raw + b"\n\n" + contract.raw, "unicode_scalars")
    assert not plan_entry(root, budget_policy=budget(count, unit="unicode_scalars"))["blockers"]
    assert plan_entry(root, budget_policy=budget(count, unit="utf8_bytes"))["blockers"]
    path.write_bytes(contract.raw)
    policy = budget(65536, selection=["AGENTS.md", "nested.md"])
    plan = plan_entry(root, budget_policy=policy)
    (root / "nested.md").write_bytes(b"changed")
    reject("plan_stale", lambda: apply_entry(root, plan, apply=True))


def fault_checks(base):
    points = ["staged", "replaced_data:AGENTS.md", "replaced:AGENTS.md", "replaced:.pf/AGENTS.md", "replaced_data:.pf/agent-entry.json", "replaced:.pf/agent-entry.json"]
    for index, point in enumerate(points):
        root = base / f"fault-{index}"
        root.mkdir()
        (root / "AGENTS.md").write_bytes(BOM + b"keep exact\r\nno newline")
        before = targets(root)
        def fault(actual, transaction):
            if actual == point:
                raise OSError("injected")
        receipt = apply_entry(root, plan_entry(root), apply=True, _fault=fault)
        assert receipt["action"] == "incomplete", receipt
        assert pending(root) == [receipt["transaction"]]
        assert rollback_entry(root, receipt["transaction"], apply=True)["action"] == "rolled_back"
        assert targets(root) == before, point
        assert not pending(root)
    root = base / "rollback-crash"
    root.mkdir()
    (root / "AGENTS.md").write_bytes(b"original")
    before = targets(root)
    receipt = apply_entry(root, plan_entry(root), apply=True)
    def fault(actual, transaction):
        if actual == "replaced_data:AGENTS.md":
            raise OSError("injected during ACL restore")
    assert rollback_entry(root, receipt["transaction"], apply=True, _fault=fault)["action"] == "incomplete"
    assert rollback_entry(root, receipt["transaction"], apply=True)["action"] == "rolled_back"
    assert targets(root) == before
    root = base / "poststage-edit"
    root.mkdir()
    (root / "AGENTS.md").write_bytes(b"original")
    def change(actual, transaction):
        if actual == "staged":
            (root / "AGENTS.md").write_bytes(b"concurrent owner change")
    receipt = apply_entry(root, plan_entry(root), apply=True, _fault=change)
    assert receipt["action"] == "incomplete" and receipt["reason"] == "precondition_changed"
    assert (root / "AGENTS.md").read_bytes() == b"concurrent owner change"
    assert not (root / ".pf/AGENTS.md").exists()
    reject("rollback_conflict", lambda: rollback_entry(root, receipt["transaction"], apply=True))
    root = base / "poststage-path"
    root.mkdir()
    external = base / "external-instruction.txt"
    external.write_bytes(b"outside target, preserve")
    def redirect(actual, transaction):
        if actual == "staged":
            os.link(external, root / "AGENTS.md")
    receipt = apply_entry(root, plan_entry(root), apply=True, _fault=redirect)
    assert receipt["action"] == "incomplete" and receipt["reason"] == "unsupported_path"
    assert external.read_bytes() == b"outside target, preserve"
    assert not (root / ".pf/AGENTS.md").exists()
    root = base / "poststage-budget"
    root.mkdir()
    (root / "nested.md").write_bytes(b"prior")
    policy = budget(9999, selection=["AGENTS.md", "nested.md"])
    def change_budget(actual, transaction):
        if actual == "staged":
            (root / "nested.md").write_bytes(b"late required instructions")
    receipt = apply_entry(root, plan_entry(root, budget_policy=policy), apply=True, _fault=change_budget)
    assert receipt["action"] == "incomplete" and receipt["reason"] == "precondition_changed"
    assert rollback_entry(root, receipt["transaction"], apply=True)["action"] == "rolled_back"
    assert (root / "nested.md").read_bytes() == b"late required instructions"
    root = base / "journal-validation"
    root.mkdir()
    receipt = apply_entry(root, plan_entry(root), apply=True)
    journal_path = root / JOURNALS / (receipt["transaction"] + ".json")
    original = journal_path.read_bytes()
    journal = json.loads(original)
    journal["payload"]["schema_version"] = 2
    journal["sha256"] = digest(encoded(journal["payload"]))
    journal_path.write_bytes(encoded(journal))
    before = targets(root)
    reject("journal_invalid", lambda: rollback_entry(root, receipt["transaction"], apply=True))
    assert targets(root) == before
    journal_path.write_bytes(original)
    (root / ".pf/AGENTS.md").write_bytes(b"later user-created content")
    before = targets(root)
    reject("rollback_conflict", lambda: rollback_entry(root, receipt["transaction"], apply=True))
    assert targets(root) == before


def platform_boundary_checks():
    from processforge_platforms.file_security import file_security_for
    try:
        file_security_for("unsupported-platform")
    except OSError:
        pass
    else:
        raise AssertionError("unknown platform must fail closed")
    # Importing the neutral boundary and selecting POSIX must not load WinAPI.
    code = ("import sys; from processforge_platforms.file_security import file_security_for; "
            "file_security_for('posix'); "
            "assert 'processforge_platforms.windows_file_security' not in sys.modules")
    result = subprocess.run([sys.executable, "-X", "utf8", "-B", "-c", code],
                            cwd=ROOT / "src", capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def windows_acl_checks(base):
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes as w
    import processforge_core.agent_entry.migration as migration
    from processforge_core.egress.windows import current_sid, verify_private
    from processforge_platforms.file_security import native_file_security

    adapter = native_file_security()
    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    convert = adv.ConvertStringSecurityDescriptorToSecurityDescriptorW
    convert.argtypes = [w.LPCWSTR, w.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(w.DWORD)]
    convert.restype = w.BOOL
    control = adv.SetSecurityDescriptorControl
    control.argtypes = [ctypes.c_void_p, w.WORD, w.WORD]
    control.restype = w.BOOL
    setter = adv.SetFileSecurityW
    setter.argtypes = [w.LPCWSTR, w.DWORD, ctypes.c_void_p]
    setter.restype = w.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    sid = current_sid()

    def configure(path, sddl):
        # Establish fixture ACLs independently, then capture the filesystem's
        # canonical bytes. SDDL's serialization is not itself a file preimage.
        pointer, size = ctypes.c_void_p(), w.DWORD()
        assert convert(sddl, 1, ctypes.byref(pointer), ctypes.byref(size))
        try:
            raw = ctypes.string_at(pointer, size.value)
            if int.from_bytes(raw[2:4], "little") & 0x0400:
                assert control(pointer, 0x0100, 0x0100)
            assert setter(str(path), 7, pointer)
        finally:
            kernel.LocalFree(pointer)
        return adapter.descriptor(path)

    parent = base / "windows-acl"
    parent.mkdir()
    # Read access for a second principal distinguishes it from private staging.
    configure(parent, f"O:{sid}G:{sid}D:PAI(A;OICI;FA;;;{sid})(A;OICI;FR;;;WD)")
    for label, flags in (("inherited", 0x0400), ("protected", 0x1000), ("protected-ai", 0x1400)):
        root = parent / label
        root.mkdir()
        target = root / "AGENTS.md"
        target.write_bytes(b"original user text\r\n")
        if flags & 0x1000:
            prefix = "PAI" if flags & 0x0400 else "P"
            configure(target, f"O:{sid}G:{sid}D:{prefix}(A;;FA;;;{sid})(A;;FR;;;WD)")
        original, descriptor = targets(root), adapter.descriptor(target)
        assert int.from_bytes(descriptor[2:4], "little") & 0x1400 == flags
        readonly = tree(root)
        planned = plan_entry(root)
        check_entry(root)
        assert tree(root) == readonly
        receipt = apply_entry(root, planned, apply=True)
        assert receipt["action"] == "applied", receipt
        assert adapter.descriptor(target) == descriptor
        verify_private(root / JOURNALS, directory=True)
        verify_private(root / ".pf/tmp" / ("agent-entry-" + receipt["transaction"]), directory=True)
        assert plan_entry(root)["status"] == "current"
        assert rollback_entry(root, receipt["transaction"], apply=True)["action"] == "rolled_back"
        assert targets(root) == original and adapter.descriptor(target) == descriptor

        def interrupt(point, transaction):
            if point == "replaced_data:AGENTS.md":
                raise OSError("interrupted between data and security restoration")
        interrupted = apply_entry(root, plan_entry(root), apply=True, _fault=interrupt)
        assert interrupted["action"] == "incomplete", interrupted
        assert rollback_entry(root, interrupted["transaction"], apply=True)["action"] == "rolled_back"
        assert targets(root) == original and adapter.descriptor(target) == descriptor
        receipt = apply_entry(root, plan_entry(root), apply=True)
        assert receipt["action"] == "applied", receipt
        assert rollback_entry(root, receipt["transaction"], apply=True, _fault=interrupt)["action"] == "incomplete"
        assert rollback_entry(root, receipt["transaction"], apply=True)["action"] == "rolled_back"
        assert targets(root) == original and adapter.descriptor(target) == descriptor

    root = parent / "concurrent-acl"
    root.mkdir()
    target = root / "AGENTS.md"
    target.write_bytes(b"preserve concurrent owner change")
    original, descriptor = targets(root), adapter.descriptor(target)
    planned = plan_entry(root)
    changed = configure(target, f"O:{sid}G:{sid}D:P(A;;FA;;;{sid})")
    reject("plan_stale", lambda: apply_entry(root, planned, apply=True))
    adapter.restore(target, descriptor)
    def concurrent_change(point, transaction):
        if point == "staged":
            adapter.restore(target, changed)
    receipt = apply_entry(root, plan_entry(root), apply=True, _fault=concurrent_change)
    assert receipt["action"] == "incomplete" and receipt["reason"] == "precondition_changed", receipt
    assert targets(root) == original and adapter.descriptor(target) == changed
    reject("rollback_conflict", lambda: rollback_entry(root, receipt["transaction"], apply=True))
    assert adapter.descriptor(target) == changed
    adapter.restore(target, descriptor)  # undo only the fixture's injected edit
    assert rollback_entry(root, receipt["transaction"], apply=True)["action"] == "rolled_back"
    with patch.object(migration, "_set_acl", side_effect=EntryError("unsupported_acl")):
        receipt = apply_entry(root, plan_entry(root), apply=True)
    assert receipt["action"] == "incomplete" and receipt["reason"] == "unsupported_acl", receipt
    assert targets(root) == original and adapter.descriptor(target) == descriptor
    assert rollback_entry(root, receipt["transaction"], apply=True)["action"] == "rolled_back"


def process_checks(base):
    root = base / "killed"
    root.mkdir()
    (root / "AGENTS.md").write_bytes(b"keep after process death")
    before = targets(root)
    child = subprocess.run([sys.executable, "-X", "utf8", "-B", __file__, "child-crash", str(root)], capture_output=True)
    assert child.returncode == 23, child.stderr
    transactions = pending(root)
    assert len(transactions) == 1
    assert rollback_entry(root, transactions[0], apply=True)["action"] == "rolled_back"
    assert targets(root) == before
    root = base / "locked"
    root.mkdir()
    plan = plan_entry(root)
    ready = base / "lock-ready"
    child = subprocess.Popen([sys.executable, "-X", "utf8", "-B", __file__, "child-lock", str(root), str(ready)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 10
        while not ready.exists() and time.monotonic() < deadline and child.poll() is None:
            time.sleep(0.02)
        assert ready.exists(), "child did not acquire lock"
        before = targets(root)
        reject("entry_writer_busy", lambda: apply_entry(root, plan, apply=True))
        assert targets(root) == before
    finally:
        child.terminate()
        child.communicate(timeout=10)
    assert apply_entry(root, plan, apply=True)["action"] == "applied", "OS did not release killed owner's lock"


def cli_checks(base):
    root = base / "cli"
    root.mkdir()
    def cli(*args):
        p = subprocess.run([sys.executable, "-X", "utf8", "-B", str(ROOT / "bin/pf.py"), "agent-entry", *args,
                            "--project-root", str(root)], capture_output=True, text=True, encoding="utf-8")
        assert not p.stderr, p.stderr
        return p.returncode, json.loads(p.stdout)
    before = tree(root)
    code, plan = cli("plan")
    assert code == 0
    assert cli("check")[0] == 0 and tree(root) == before
    plan_file = base / "approved-plan.json"
    plan_file.write_bytes(encoded(plan))
    assert cli("apply", "--plan-file", str(plan_file))[1]["reason"] == "explicit_apply_required"
    assert tree(root) == before
    code, receipt = cli("apply", "--plan-file", str(plan_file), "--apply")
    assert code == 0 and receipt["action"] == "applied", receipt
    assert cli("check")[1]["entry"] == "current"
    assert cli("rollback", "--transaction", receipt["transaction"], "--apply")[1]["action"] == "rolled_back"
    assert all(raw is None for raw in targets(root).values())


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "child-crash":
        root = Path(sys.argv[2])
        def crash(point, transaction):
            if point == "replaced_data:AGENTS.md":
                os._exit(23)
        apply_entry(root, plan_entry(root), apply=True, _fault=crash)
        return 2
    if len(sys.argv) > 1 and sys.argv[1] == "child-lock":
        with entry_lock(Path(sys.argv[2])):
            Path(sys.argv[3]).write_text("locked", encoding="utf-8")
            time.sleep(30)
        return 0
    with tempfile.TemporaryDirectory(prefix="pf-agent-entry-") as temporary:
        base = Path(temporary)
        contract, source = source_checks(base)
        ownership_checks(base, contract)
        conflict_checks(base, contract, source)
        budget_checks(base, contract)
        platform_boundary_checks()
        windows_acl_checks(base)
        fault_checks(base)
        process_checks(base)
        cli_checks(base)
    print("PASS: source/hash/renderer, ownership/user bytes, paths/ACL, platform boundary, inherited/protected ACL recovery, read-only CLI, budgets, stale plans, fault rollback, process death and OS lock")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
