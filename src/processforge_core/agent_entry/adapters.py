"""Explicit, bounded client entry placement; never invokes or configures a client."""
from __future__ import annotations

import os
from pathlib import Path
import re

from .contract import (BOM, EntryError, decode_json, digest, encoded,
                          inspect_projection, load_contract, text_bytes)
from .migration import (MAX_FILE, TARGETS, _apply_placement, budgets,
                                    manifest, pending, policy_input, project_identity,
                                    read_file, root_path, safe_path)
from .profiles import adapter_spec, diagnose_entry


def project_adapter_content(before: bytes | None, spec: dict) -> tuple[bytes, str]:
    """Keep every user byte; only the exact versioned block establishes ownership."""
    generated = spec["generated_section"].encode("utf-8")
    if before is None:
        return generated, "create"
    text_bytes(before)
    offset = len(BOM) if before.startswith(BOM) else 0
    body = before[offset:]
    outside = body
    owned = b"PF:ADAPTER:" in body
    if owned:
        end = re.search(rb"(?m)^<!-- PF:ADAPTER:END -->(?:\r?\n|$)", body)
        if (body.count(b"PF:ADAPTER:") != 2 or end is None
                or body[:end.end()].replace(b"\r\n", b"\n").rstrip(b"\n") != generated.rstrip(b"\n")):
            raise EntryError("adapter_managed_content_conflict", spec["target"])
        outside = body[end.end():]
    # Deliberately conservative, including literal/code examples: this is a
    # duplicate-risk check, NOT a substitute for either client's Markdown parser.
    if re.search(rb"@(?:\./)?AGENTS\.md", outside, re.IGNORECASE):
        raise EntryError("adapter_unmanaged_import_candidate", spec["target"])
    if owned:
        return before, "unchanged"
    # Inserting at the beginning avoids inheriting an unclosed user code fence.
    return before[:offset] + generated + b"\n" + body, "prepend_block"


def _current_entry(root: Path, contract):
    inputs, content = {}, {}
    for name in TARGETS:
        raw, inputs[name] = read_file(root, name)
        content[name] = raw
        if name != TARGETS[-1]:
            if inspect_projection(raw, contract)["status"] != "verified":
                raise EntryError("entry_migration_required", name)
        else:
            value = decode_json(raw) if raw is not None else None
            if (not isinstance(value, dict) or type(value.get("schema_version")) is not int
                    or value != manifest(contract)):
                raise EntryError("entry_migration_required", name)
    return inputs, content["AGENTS.md"]


def _source_digest(spec, contract):
    return digest(encoded({"contract_source": contract.source_digest, "adapter": spec}))


def _adapter_plan(root: Path, profile_id: str, route: str, policies: list):
    spec = adapter_spec(profile_id, route)
    if spec["target"] is None:
        raise EntryError("adapter_guidance_only")
    contract = load_contract()
    inputs, root_raw = _current_entry(root, contract)
    name = spec["target"]
    before, pre = read_file(root, name, writable=True)
    after, action = project_adapter_content(before, spec)
    if len(after) > MAX_FILE:
        raise EntryError("output_too_large", name)
    raw_budget, budget_inputs, blockers = budgets(root, {name: after, "AGENTS.md": root_raw}, policies, contract)
    inputs.update(budget_inputs)
    interrupted = pending(root)
    if interrupted:
        blockers.append("entry_transaction_incomplete")
    # A preview of exactly one substitution, not recursive/native expansion.
    reference = spec["generated_section"].splitlines()[1].encode()
    at = after.index(reference)
    projection = inspect_projection(root_raw, contract)
    budget = {"status": "budget_unverified", "reason": "native_expansion_not_observed",
              "unit": "utf8_bytes", "vendor_file_bytes": len(after), "root_file_bytes": len(root_raw),
              "single_import_preview_bytes": len(after) - len(reference) + len(root_raw),
              "preview_k_start": at + projection["k_start"], "preview_k_end": at + projection["k_end"],
              "expanded_bytes": None, "contract_complete": None, "required_instructions_complete": None,
              "raw_policy": raw_budget}
    plan = {"schema_version": 1, "kind": "pf.agent-entry.adapter-plan", "project": project_identity(root),
            "adapter": spec, "source_digest": _source_digest(spec, contract),
            "contract_version": contract.version, "contract_sha256": contract.sha256,
            "preconditions": {name: pre}, "budget_inputs": inputs, "budget_policy": policies, "budget": budget,
            "files": [{"path": name, "action": action, "before_sha256": pre["sha256"], "after_sha256": digest(after)}],
            "blockers": sorted(set(blockers)), "pending_transactions": interrupted,
            "delivery": "unverified", "behavior": "unverified",
            "status": "conflict" if blockers else "current" if before == after else "planned"}
    plan["digest"] = digest(encoded(plan))
    return plan, {name: before}, {name: after}


def plan_adapter(project: Path, *, profile_id: str, route: str, budget_policy=None) -> dict:
    return _adapter_plan(root_path(project), profile_id, route, policy_input(budget_policy))[0]


def apply_adapter(project: Path, supplied: dict, *, apply: bool = False, _fault=None) -> dict:
    if not isinstance(supplied, dict) or not isinstance(supplied.get("adapter"), dict):
        raise EntryError("plan_invalid")
    profile_id, route = supplied["adapter"].get("profile_id"), supplied["adapter"].get("route")
    spec = adapter_spec(profile_id, route)
    if spec["target"] is None:
        raise EntryError("adapter_guidance_only")
    return _apply_placement(project, supplied, apply=apply, targets=(spec["target"],),
                            planner=lambda root: _adapter_plan(root, profile_id, route, policy_input(supplied.get("budget_policy"))),
                            source_guard=lambda: _source_digest(adapter_spec(profile_id, route), load_contract()), _fault=_fault)


def adapter_guide(project: Path, *, profile_id: str, route: str, cwd: str = ".", observation=None) -> dict:
    spec = adapter_spec(profile_id, route)
    root = root_path(project)
    current = root if cwd == "." else safe_path(root, cwd)
    if not current.is_dir():
        raise EntryError("cwd_missing")
    diagnostics = diagnose_entry(root, profile_id=profile_id, observation=observation, cwd=cwd)
    blockers = list(diagnostics["blockers"])
    interrupted = pending(root)
    if interrupted:
        blockers.append("entry_transaction_incomplete")
    if route == "root-agents" and profile_id in {"P-CLAUDE", "P-GEMINI"}:
        vendor = "CLAUDE.md" if profile_id == "P-CLAUDE" else "GEMINI.md"
        raw, _ = read_file(root, vendor)
        if raw and (b"PF:ADAPTER:" in raw or re.search(rb"@(?:\./)?AGENTS\.md", raw, re.IGNORECASE)):
            blockers.append("adapter_route_conflict")
    argv = None
    if route == "explicit-read":
        relative = Path(os.path.relpath(root / "AGENTS.md", current)).as_posix()
        argv = ["aider", "--read", relative if relative.startswith("../") else "./" + relative]
    return {"schema_version": 1, "kind": "pf.agent-entry.adapter-guide", "adapter": spec,
            "cwd": cwd, "argv": argv, "status": "blocked" if blockers else "guidance",
            "blockers": sorted(set(blockers)), "pending_transactions": interrupted,
            "delivery": "unverified", "behavior": "unverified", "diagnostics": diagnostics}
