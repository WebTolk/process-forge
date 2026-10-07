#!/usr/bin/env python3
"""Behavioral Work resource binding, isolation and read-only regression."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from processforge_core.resources.local_search import authorized_coverage, build_index, index_status
from processforge_core.process_execution import ProcessExecutionService, canonical_fingerprint
from processforge_core.work.resource_material import DEFAULT_LIMITS, MaterialBudget, MaterialError, capture_material
from processforge_core.work.resources import WorkResourceService
import processforge as core
from process_execution_smoke_support import assignment, fixture, run
from garage_search_smoke_support import register_fixture_resource, run_cli, select_fixture_resource
from smoke_garage_mode_not_promoted_by_session import call_mcp


def require(ok: bool, detail: Any) -> None:
    if not ok:
        raise AssertionError(detail)


def mcp_raw(workplace: Path, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    requests = [{"jsonrpc": "2.0", "id": 1, "method": "initialize"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": name, "arguments": arguments}}]
    result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/pf_runtime/mcp_server.py"), "--workplace", str(workplace)],
                            cwd=ROOT, input="\n".join(json.dumps(item) for item in requests) + "\n", text=True,
                            encoding="utf-8", capture_output=True, timeout=120)
    require(result.returncode == 0, result.stderr)
    response = [json.loads(line) for line in result.stdout.splitlines() if line.strip()][-1]
    if "error" in response:
        return {"rpc_error": response["error"]}
    content = response.get("result", {}).get("content", [{}])[0].get("text", "")
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        payload = {"message": content}
    return {"tool_error": payload} if response.get("result", {}).get("isError") else payload


def configure_resource(workplace: Path, package_id: str, resource_id: str, policy: dict[str, Any]) -> Path:
    manifest_path = workplace / "packages" / package_id / "package.yaml"
    document = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    resource = next(item for item in document["resources"] if item.get("id") == resource_id)
    resource["indexing"] = copy.deepcopy(policy)
    manifest_path.write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return manifest_path


def configure_legacy_policy(workplace: Path, package_id: str, resource_id: str, policy: str) -> Path:
    manifest_path = workplace / "packages" / package_id / "package.yaml"
    document = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    resource = next(item for item in document["resources"] if item.get("id") == resource_id)
    resource.pop("indexing", None)
    resource["index_policy"] = policy
    manifest_path.write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return manifest_path


def checkin(workplace: Path, project: Path, agent: str, session: str) -> None:
    run_cli("agent-checkin", "--workplace", str(workplace), "--agent", agent, "--session", session,
            "--project-root", str(project), "--role", "worker")


def selectors(project: Path, work: dict[str, Any], *, session: str | None = None) -> dict[str, Any]:
    value = {"project_root": str(project), "run_id": work["run_id"], "assignment_id": work["assignment_id"],
             "context_id": work["context"]["id"]}
    if session:
        value["session_id"] = session
    return value


def read_error(service: WorkResourceService, args: dict[str, Any], expected: str, **options: Any) -> dict:
    result = service.read(**args, **options)
    require(result.get("status") == "blocked" and result.get("reason") == expected, {"expected": expected, "actual": result})
    return result


def change_capsule(project: Path, work: dict[str, Any], edit) -> tuple[bytes, bytes, bytes]:
    flow = project / ".pf"
    cap_path = flow / "contexts" / "assignment-capsules" / f"{work['assignment_id']}.capsule.yaml"
    assignment_path = flow / "assignments" / f"{work['assignment_id']}.yaml"
    run_path = flow / "runs" / work["run_id"] / "run.yaml"
    original = (cap_path.read_bytes(), assignment_path.read_bytes(), run_path.read_bytes())
    cap, task, run_doc = [yaml.safe_load(item) for item in original]
    edit(cap, task, run_doc)
    cap_path.write_text(yaml.safe_dump(cap, allow_unicode=True, sort_keys=False), encoding="utf-8")
    task["process_execution"]["assignment_capsule_checksum"] = "sha256:" + hashlib.sha256(cap_path.read_bytes()).hexdigest()
    assignment_path.write_text(yaml.safe_dump(task, allow_unicode=True, sort_keys=False), encoding="utf-8")
    run_path.write_text(yaml.safe_dump(run_doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return original


def restore_capsule(project: Path, work: dict[str, Any], original: tuple[bytes, bytes, bytes]) -> None:
    flow = project / ".pf"
    (flow / "contexts" / "assignment-capsules" / f"{work['assignment_id']}.capsule.yaml").write_bytes(original[0])
    (flow / "assignments" / f"{work['assignment_id']}.yaml").write_bytes(original[1])
    (flow / "runs" / work["run_id"] / "run.yaml").write_bytes(original[2])


def set_subset(cap: dict, task: dict, run_doc: dict, values: list[str]) -> None:
    definition = cap["process_execution"]["definition"]
    stage = next(item for item in definition["stages"] if item["id"] == task["stage"])
    stage["resource_subset"] = list(values)
    fingerprint = canonical_fingerprint(definition)
    for doc in (cap["process_execution"], task["process_execution"], run_doc["process_execution"]):
        doc["definition"] = copy.deepcopy(definition)
        doc["process_fingerprint"] = fingerprint
    # This helper constructs a coherent synthetic context, not a tamper case.
    # T03 additionally binds the process identity inside the complete contract.
    if "execution_contract" in cap:
        from processforge_core.work.context import fingerprint as contract_fingerprint
        contract = cap["execution_contract"]
        contract["process"]["fingerprint"] = fingerprint
        contract["contract_checksum"] = contract_fingerprint({key: value for key, value in contract.items() if key != "contract_checksum"})


def resource_order_checks() -> None:
    """Declaration order must not change grants, including older native pins."""
    with fixture() as (workplace, project, _initial):
        declared = []
        for package, resource in [("fixture.order-z", "z-guide"), ("fixture.order-a", "a-guide")]:
            declared.append(register_fixture_resource(workplace, package, resource,
                            {"guide.md": "ResourceOrderNeedle"}, title=resource))
            configure_resource(workplace, package, resource,
                               {"enabled": True, "mode": "fulltext", "sources": [{"path": ".", "mode": "fulltext", "include": ["**/*.md"]}]})
            select_fixture_resource(project, workplace, package, resource)
        work = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "Nonalphabetic resource order"})
        require(work.get("action") == "created_new", work)
        args = {key: value for key, value in selectors(project, work).items() if key != "project_root"}
        cap_path = project / ".pf/contexts/assignment-capsules" / f"{work['assignment_id']}.capsule.yaml"
        task_path = project / ".pf/assignments" / f"{work['assignment_id']}.yaml"
        run_path = project / ".pf/runs" / work["run_id"] / "run.yaml"
        cap = yaml.safe_load(cap_path.read_bytes())
        canonical = sorted(declared)
        require(cap["context"]["selected_resource_ids"] == canonical, cap["context"])
        require(cap["process_execution"]["selected_resource_ids"] == canonical, cap["process_execution"])
        require(run(project, work)["process_execution"]["selected_resource_ids"] == canonical, run(project, work))
        service = WorkResourceService(project, workplace, core)

        def read(expected: str = "ready") -> None:
            before = {path: path.read_bytes() for path in (cap_path, task_path, run_path)}
            result = service.read(operation="resolve", **args, resource_id=declared[0])
            require(result.get("status") == "ready" if expected == "ready" else
                    result.get("status") == "blocked" and result.get("reason") == expected, result)
            require(all(path.read_bytes() == raw for path, raw in before.items()), "resource read changed Work state")

        read()
        found = service.read(operation="search", **args, query="ResourceOrderNeedle")
        require(found.get("status") == "ready" and found.get("total") == 2, found)

        def old_order(cap, task, run_doc):
            cap["process_execution"]["selected_resource_ids"] = list(declared)
            run_doc["process_execution"]["selected_resource_ids"] = list(declared)

        old = change_capsule(project, work, old_order)
        try:
            state = ProcessExecutionService(project, workplace, core).state(run_id=work["run_id"], assignment_id=work["assignment_id"])
            require(state["context"]["validation"]["status"] == "valid", state)
            read()  # Existing native capsules remain byte-identical and usable.
        finally:
            restore_capsule(project, work, old)

        invalid = [canonical[:1], canonical + ["not-selected"], [canonical[0], canonical[0]],
                   "not-a-list", [None], [1], [""], [f"id-{i}" for i in range(65)]]
        for location in ("capsule_pin", "run_pin", "context"):
            for value in invalid:
                def corrupt(cap, task, run_doc):
                    target = cap["context"] if location == "context" else (cap if location == "capsule_pin" else run_doc)["process_execution"]
                    target["selected_resource_ids"] = copy.deepcopy(value)
                old = change_capsule(project, work, corrupt)
                try:
                    read("resource_scope_invalid")
                finally:
                    restore_capsule(project, work, old)

        def binding_change(cap, task, run_doc, mode):
            resources = cap["resource_bindings"]["resources"]
            if mode == "reverse":
                resources.reverse()
            elif mode == "missing":
                resources.pop()
            elif mode == "extra":
                resources.append({**copy.deepcopy(resources[0]), "id": "not-selected"})
            elif mode == "duplicate":
                resources.append(copy.deepcopy(resources[0]))
            else:
                resources[0]["id"] = None
            # Coherent synthetic fixtures exercise membership, not stale digests.
            from processforge_core.work.context import fingerprint
            contract = cap["execution_contract"]
            contract["resources"]["bindings_checksum"] = fingerprint(cap["resource_bindings"])
            contract["contract_checksum"] = fingerprint({k: v for k, v in contract.items() if k != "contract_checksum"})

        for mode in ("reverse", "missing", "extra", "duplicate", "invalid"):
            old = change_capsule(project, work, lambda cap, task, run_doc: binding_change(cap, task, run_doc, mode))
            try:
                read("ready" if mode == "reverse" else "resource_binding_invalid")
            finally:
                restore_capsule(project, work, old)


def legacy_full_text_policy_checks() -> None:
    """Legacy full_text declarations stay fulltext through Work materialization."""
    with fixture() as (workplace, project, _initial):
        records = []
        for suffix, policy, needle in (
            ("underscore", "full_text", "LegacyUnderscoreNeedle"),
            ("canonical", "fulltext", "LegacyCanonicalNeedle"),
        ):
            package, resource = f"fixture.legacy-{suffix}", f"guide-{suffix}"
            rid = register_fixture_resource(workplace, package, resource, {"guide.md": needle}, title=f"Legacy {policy} Guide")
            configure_legacy_policy(workplace, package, resource, policy)
            select_fixture_resource(project, workplace, package, resource)
            records.append((rid, package, resource, needle))

        work = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "Legacy fulltext policies pin fulltext"})
        require(work.get("action") == "created_new", work)
        args = selectors(project, work)
        cap_path = project / ".pf" / "contexts" / "assignment-capsules" / f"{work['assignment_id']}.capsule.yaml"
        cap = yaml.safe_load(cap_path.read_bytes())
        bindings = {item["id"]: item for item in cap["resource_bindings"]["resources"]}
        service = WorkResourceService(project, workplace, core)
        for rid, package, resource, needle in records:
            binding = bindings[rid]
            require(binding["status"] == "available" and binding["material_kind"] == "fulltext", binding)
            require(binding.get("manifest"), binding)
            require(binding["indexing"]["mode"] == "fulltext", binding)
            require(binding["indexing"]["sources"][0]["mode"] == "fulltext", binding)

            found = service.read(operation="search", **{key: args[key] for key in ("run_id", "assignment_id", "context_id")}, query=needle)
            require(found.get("status") == "ready" and found.get("total") == 1, found)
            resolved = service.read(operation="resolve", **{key: args[key] for key in ("run_id", "assignment_id", "context_id")}, resource_id=rid)
            require(resolved.get("status") == "ready" and resolved["resource"]["navigation"] == "verified_declared_material", resolved)
            root = workplace / "packages" / package / "resources" / resource
            captured, _ = capture_material(binding, root, {"package": package, "relative_path": f"resources/{resource}"}, include_content=True)
            require(captured["material_kind"] == "fulltext" and captured["manifest"] == binding["manifest"], captured)


def main() -> int:
    resource_order_checks()
    legacy_full_text_policy_checks()
    with tempfile.TemporaryDirectory(prefix="pf-work-resource-binding-") as raw:
        root = Path(raw)
        with fixture() as (workplace, project, _fixture_work):
            package_a, package_b = "fixture.t02-a", "fixture.t02-b"
            aid = register_fixture_resource(workplace, package_a, "guide", {"guide.md": "AFulltextNeedle"}, title="T02 A Guide")
            aroot = workplace / "packages" / package_a / "resources" / "guide"
            configure_resource(workplace, package_a, "guide", {"enabled": True, "mode": "fulltext", "sources": [{"path": ".", "mode": "fulltext", "include": ["**/*.md"]}]})
            select_fixture_resource(project, workplace, package_a, "guide")
            work_a = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "T02 Work A pins A"})
            require(work_a.get("action") == "created_new", work_a)
            args_a = selectors(project, work_a)
            cap_a = project / ".pf" / "contexts" / "assignment-capsules" / f"{work_a['assignment_id']}.capsule.yaml"
            cap_a_bytes = cap_a.read_bytes()
            cap_a_doc = yaml.safe_load(cap_a_bytes)
            bind_a = {item["id"]: item for item in cap_a_doc["resource_bindings"]["resources"]}
            require(aid in bind_a and bind_a[aid]["status"] == "available" and bind_a[aid]["material_kind"] == "fulltext", bind_a)
            capture_reference_a = {"package": package_a, "relative_path": "resources/guide"}
            binding_without_docs, _ = capture_material(bind_a[aid], aroot, capture_reference_a, include_content=False)
            binding_with_docs, _ = capture_material(bind_a[aid], aroot, capture_reference_a, include_content=True)
            require(binding_without_docs == binding_with_docs, {"without_docs": binding_without_docs, "with_docs": binding_with_docs})

            read_a = call_mcp(workplace, "pf.work.search", {**args_a, "query": "AFulltextNeedle"})
            require(read_a.get("status") == "ready" and read_a.get("total") == 1, read_a)
            cli_a = run_cli("work-search", "--project-root", str(project), "--workplace", str(workplace),
                            "--run", work_a["run_id"], "--assignment", work_a["assignment_id"],
                            "--context-id", work_a["context"]["id"], "--query", "AFulltextNeedle", "--json")
            require(json.loads(cli_a.stdout) == read_a, {"mcp": read_a, "cli": cli_a.stdout})
            resolve_a = call_mcp(workplace, "pf.work.resolve", {**args_a, "resource_id": aid})
            require(resolve_a.get("status") == "ready" and resolve_a["resource"]["navigation"] == "verified_declared_material", resolve_a)
            proof_path = project / ".pf" / "artifacts" / "t02-resource-proof.md"
            proof_path.parent.mkdir(parents=True, exist_ok=True)
            proof_path.write_text("Verified resource read provenance\n", encoding="utf-8")
            evidence = [{"kind": "artifact", "artifact_id": "brief", "status": "ready", "summary": "A material searched",
                         "path": ".pf/artifacts/t02-resource-proof.md", "resource_provenance": resolve_a["resource_provenance"][0]},
                        {"kind": "gate", "gate_id": "prepare-ready", "status": "passed", "summary": "prepare passed"}]
            progressed = call_mcp(workplace, "pf.work.transition", {"project_root": str(project), "outcome": "completed", "evidence": evidence})
            require(progressed.get("action") == "stage_transitioned" and progressed.get("next_stage_id") == "build", progressed)
            history_evidence = assignment(project, work_a).get("stage_history", [])[0]["evidence"]
            require(next(item for item in history_evidence if item.get("artifact_id") == "brief").get("resource_provenance") == resolve_a["resource_provenance"][0], history_evidence)
            continued = call_mcp(workplace, "pf.work.resolve", {**args_a, "resource_id": aid})
            require(continued.get("status") == "ready" and continued["work"]["stage_id"] == "build", continued)
            require(cap_a.read_bytes() == cap_a_bytes, "legitimate Work operations changed pinned capsule bytes")

            session_a, session_a2 = "t02-session-a", "t02-session-a2"
            checkin(workplace, project, "t02-agent-a", session_a)
            checkin(workplace, project, "t02-agent-a2", session_a2)
            continued_session = call_mcp(workplace, "pf.work.search", {**selectors(project, work_a, session=session_a2), "query": "AFulltextNeedle"})
            require(continued_session.get("work", {}).get("stage_id") == "build", continued_session)
            normalize = copy.deepcopy
            comparable_original, comparable_continued = normalize(read_a), normalize(continued_session)
            for result in (comparable_original, comparable_continued):
                result.get("work", {}).pop("stage_id", None)
                for provenance in result.get("resource_provenance", []):
                    provenance.pop("stage_id", None)
                for item in result.get("items", []):
                    item.get("resource_provenance", {}).pop("stage_id", None)
                for item in result.get("results", []):
                    item.get("resource_provenance", {}).pop("stage_id", None)
            require(comparable_continued == comparable_original, {"original": read_a, "continued": continued_session})
            wrong_selector = WorkResourceService(project, workplace, core).read(operation="resolve", run_id=work_a["run_id"],
                assignment_id=work_a["assignment_id"], context_id="wrong-context-id", resource_id=aid)
            require(wrong_selector.get("reason") == "work_context_mismatch", wrong_selector)
            missing_selector = WorkResourceService(project, workplace, core).read(operation="resolve", run_id="", assignment_id=work_a["assignment_id"],
                context_id=work_a["context"]["id"], resource_id=aid)
            require(missing_selector.get("reason") == "work_selector_required", missing_selector)

            package_b, resource_b, bid = "fixture.t02-b", "manual", "fixture.t02-b:manual"
            register_fixture_resource(workplace, package_b, resource_b, {"readme.md": "BMetadataBodyOriginal"}, title="T02 B MetadataTitleMarker")
            broot = workplace / "packages" / package_b / "resources" / resource_b
            configure_resource(workplace, package_b, resource_b, {"enabled": True, "mode": "metadata", "sources": [{"path": ".", "mode": "metadata"}]})
            select_fixture_resource(project, workplace, package_b, resource_b)
            work_b = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "T02 Work B pins A and B"})
            require(work_b.get("action") == "created_new" and work_b["context"]["id"] != work_a["context"]["id"], work_b)
            args_b = selectors(project, work_b)
            service = WorkResourceService(project, workplace, core)
            cannot_get_b = read_error(service, {key: args_a[key] for key in ("run_id", "assignment_id", "context_id")},
                                      "resource_not_in_work", operation="resolve", resource_id=bid)
            require(cannot_get_b.get("work", {}).get("context_id") == work_a["context"]["id"], cannot_get_b)
            read_b = service.read(operation="resolve", **{key: args_b[key] for key in ("run_id", "assignment_id", "context_id")}, resource_id=bid)
            require(read_b.get("status") == "ready" and read_b["resource"]["material_kind"] == "metadata", read_b)
            body_before = (broot / "readme.md").read_text(encoding="utf-8")
            body_fingerprint = read_b["resource"]["material_fingerprint"]
            (broot / "readme.md").write_text("BMetadataBodyMutated", encoding="utf-8")
            read_b_after = service.read(operation="resolve", **{key: args_b[key] for key in ("run_id", "assignment_id", "context_id")}, resource_id=bid)
            no_body = service.read(operation="search", **{key: args_b[key] for key in ("run_id", "assignment_id", "context_id")}, query="BMetadataBodyMutated")
            require(read_b_after.get("status") == "ready" and read_b_after["resource"]["material_fingerprint"] == body_fingerprint, read_b_after)
            require(no_body.get("status") == "ready" and no_body.get("total") == 0, no_body)
            (broot / "readme.md").write_text(body_before, encoding="utf-8")

            no_b_in_a = service.read(operation="resolve", **{key: args_a[key] for key in ("run_id", "assignment_id", "context_id")}, resource_id=bid)
            require(no_b_in_a.get("reason") == "resource_not_in_work", no_b_in_a)
            a_text = (aroot / "guide.md").read_text(encoding="utf-8")
            (aroot / "guide.md").write_text("AFulltextChanged", encoding="utf-8")
            changed = service.read(operation="search", **{key: args_a[key] for key in ("run_id", "assignment_id", "context_id")}, query="AFulltextNeedle")
            require(changed.get("reason") == "resource_material_changed", changed)
            (aroot / "guide.md").write_text(a_text, encoding="utf-8")
            (aroot / "guide.md").unlink()
            deleted = service.read(operation="search", **{key: args_a[key] for key in ("run_id", "assignment_id", "context_id")}, query="AFulltextNeedle")
            require(deleted.get("reason") == "resource_material_changed", deleted)
            (aroot / "guide.md").write_text(a_text, encoding="utf-8")

            # Material generation changes are detected against current authorized metadata.
            manifest_a = workplace / "packages" / package_a / "package.yaml"
            package_doc = yaml.safe_load(manifest_a.read_text(encoding="utf-8"))
            entry_a = next(item for item in package_doc["resources"] if item.get("id") == "guide")
            original_version = entry_a.get("version")
            entry_a["version"] = "2.0.0"
            manifest_a.write_text(yaml.safe_dump(package_doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
            run_cli("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace), "--apply")
            generation_change = service.read(operation="resolve", **{key: args_a[key] for key in ("run_id", "assignment_id", "context_id")}, resource_id=aid)
            require(generation_change.get("reason") == "resource_generation_changed", generation_change)
            package_doc = yaml.safe_load(manifest_a.read_text(encoding="utf-8"))
            entry_a = next(item for item in package_doc["resources"] if item.get("id") == "guide")
            if original_version is None:
                entry_a.pop("version", None)
            else:
                entry_a["version"] = original_version
            manifest_a.write_text(yaml.safe_dump(package_doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
            run_cli("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace), "--apply")

            project_manifest = project / ".pf" / "process-forge.yaml"
            original_manifest = project_manifest.read_bytes()
            manifest_doc = yaml.safe_load(original_manifest)
            reqs = manifest_doc["context_requirements"]["knowledge_resources"]
            manifest_doc["context_requirements"]["knowledge_resources"] = [item for item in reqs if item.get("id") != "guide"]
            project_manifest.write_text(yaml.safe_dump(manifest_doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
            run_cli("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace), "--apply")
            revoked = service.read(operation="resolve", **{key: args_a[key] for key in ("run_id", "assignment_id", "context_id")}, resource_id=aid)
            require(revoked.get("reason") == "resource_access_revoked", revoked)
            project_manifest.write_bytes(original_manifest)
            run_cli("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace), "--apply")
            require(cap_a.read_bytes() == cap_a_bytes, "refresh/revocation changed Work A capsule")

            # Explicit [] is a valid no-grant subset; a subset outside the pin is invalid.
            work_c = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "T02 synthetic subset negatives"})
            args_c = selectors(project, work_c)
            original_b = change_capsule(project, work_b, lambda cap, task, run_doc: set_subset(cap, task, run_doc, []))
            empty_search = service.read(operation="search", **{key: args_b[key] for key in ("run_id", "assignment_id", "context_id")}, query="AFulltextNeedle")
            empty_resolve = service.read(operation="resolve", **{key: args_b[key] for key in ("run_id", "assignment_id", "context_id")}, resource_id=bid)
            require(empty_search.get("status") == "ready" and empty_search.get("coverage", {}).get("status") == "empty" and empty_search.get("total") == 0, empty_search)
            require(empty_resolve.get("reason") == "resource_not_in_stage", empty_resolve)
            restore_capsule(project, work_b, original_b)
            original_c = change_capsule(project, work_c, lambda cap, task, run_doc: set_subset(cap, task, run_doc, ["not-pinned-resource"]))
            expanded = service.read(operation="search", **{key: args_c[key] for key in ("run_id", "assignment_id", "context_id")}, query="AFulltextNeedle")
            require(expanded.get("reason") == "stage_resource_subset_invalid", expanded)
            restore_capsule(project, work_c, original_c)

            # Exact capsule integrity/legacy compatibility error classes.
            original_c = change_capsule(project, work_c, lambda cap, _task, _run_doc: cap["resource_bindings"].update(schema_version=99))
            unknown_version = service.read(operation="search", **{key: args_c[key] for key in ("run_id", "assignment_id", "context_id")}, query="AFulltextNeedle")
            require(unknown_version.get("reason") == "resource_binding_version_unsupported", unknown_version)
            restore_capsule(project, work_c, original_c)
            original_c = change_capsule(project, work_c, lambda cap, _task, _run_doc: cap.pop("resource_bindings"))
            legacy = service.read(operation="search", **{key: args_c[key] for key in ("run_id", "assignment_id", "context_id")}, query="AFulltextNeedle")
            require(legacy.get("reason") == "legacy_contract_incomplete", legacy)
            restore_capsule(project, work_c, original_c)
            cap_c = project / ".pf" / "contexts" / "assignment-capsules" / f"{work_c['assignment_id']}.capsule.yaml"
            exact_c = cap_c.read_bytes()
            cap_c.write_bytes(exact_c + b"\n# tampered without pin update\n")
            checksum = service.read(operation="search", **{key: args_c[key] for key in ("run_id", "assignment_id", "context_id")}, query="AFulltextNeedle")
            require(checksum.get("reason") == "work_context_checksum_mismatch", checksum)
            cap_c.write_bytes(exact_c)

            # Work material path and request bounds fail closed; no private path is returned in the reason.
            traversal = {"id": "fixture:bad", "kind": "documentation", "indexing": {"mode": "fulltext", "sources": [{"path": "../outside", "mode": "fulltext"}]}}
            try:
                capture_material(traversal, aroot, {"package": package_a, "relative_path": "resources/guide"})
            except MaterialError as exc:
                require(exc.code == "resource_material_path_invalid", exc.code)
            else:
                raise AssertionError("traversal source accepted")
            for binding, resource_root, reference in (
                (bind_a[aid], aroot, {"package": package_a, "relative_path": "resources/guide"}),
                ({item["id"]: item for item in yaml.safe_load((project / ".pf" / "contexts" / "assignment-capsules" / f"{work_b['assignment_id']}.capsule.yaml").read_bytes())["resource_bindings"]["resources"]}[bid],
                 broot, {"package": package_b, "relative_path": f"resources/{resource_b}"}),
            ):
                for include_content in (False, True):
                    bounded = MaterialBudget()
                    bounded.document_bytes = DEFAULT_LIMITS["document_bytes"]
                    try:
                        capture_material(binding, resource_root, reference, include_content=include_content, budget=bounded)
                    except MaterialError as exc:
                        require(exc.code == "resource_material_budget_exceeded", {"code": exc.code, "mode": binding["material_kind"], "include_content": include_content})
                    else:
                        raise AssertionError({"error": "exhausted document-byte budget accepted", "mode": binding["material_kind"], "include_content": include_content})
            escape = root / "outside.md"
            escape.write_text("never indexed", encoding="utf-8")
            link = aroot / "outside-link.md"
            try:
                link.symlink_to(escape)
            except OSError:
                symlink_case = "unsupported by host"
            else:
                try:
                    capture_material({**traversal, "indexing": {"mode": "fulltext", "sources": [{"path": ".", "mode": "fulltext", "include": ["**/*.md"]}]}},
                                     aroot, {"package": package_a, "relative_path": "resources/guide"})
                except MaterialError as exc:
                    require(exc.code == "resource_material_path_invalid", exc.code)
                    symlink_case = "rejected"
                else:
                    raise AssertionError("symlink escape accepted")
                link.unlink()

            # A fresh Workplace index and an unindexed project grant are different facts.
            workplace_snapshot = core.workplace_search_runtime_snapshot(workplace)
            build_index(workplace, workplace_snapshot, workplace_root=workplace)
            global_status = index_status(workplace, workplace_snapshot, workplace_root=workplace)
            grant_snapshot = {"local_search_resources": [{"id": aid}, {"id": "project-local-unindexed"}]}
            coverage = authorized_coverage(project, grant_snapshot, workplace_root=workplace)
            require(global_status.get("status") == "fresh" and coverage.get("status") == "partial"
                    and coverage.get("missing_resource_ids") == ["project-local-unindexed"], {"global": global_status, "coverage": coverage})

            other = root / "other-project"
            run_cli("project-onboard", "--project-root", str(other), "--workplace", str(workplace), "--type", "generic", "--apply")
            checkin(workplace, other, "t02-agent-other", "t02-session-other")
            denied = mcp_raw(workplace, "pf.work.search", {**selectors(project, work_a, session="t02-session-other"), "query": "AFulltextNeedle"})
            require(denied.get("tool_error", {}).get("error", {}).get("code") == "session_project_mismatch", denied)
            require(cap_a.read_bytes() == cap_a_bytes, "denied or synthetic reads changed original pinned capsule")

    print("PASS: Work resource binding isolation/pinning/current access/metadata/fulltext/subsets/provenance; symlink=" + symlink_case)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
