#!/usr/bin/env python3
"""Focused behavioral coverage for bounded prepared worker input and collection."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from smoke_conversation_completeness import setup_basic_project, pf
from garage_search_smoke_support import register_fixture_resource, select_fixture_resource
import processforge as core


RUN_ID = "prepared-run"
SCHEMA_PATH = ROOT / "schemas" / "prepared-input.schema.json"


def require(condition: bool, detail: Any) -> None:
    if not condition:
        raise AssertionError(detail)


def call(project: Path, task: str, operation: str, **options: Any) -> tuple[int, str]:
    values = {
        "project_root": str(project), "task": task,
        "driver": options.get("driver"), "executable": options.get("executable"),
        "model": options.get("model"), "reasoning_effort": options.get("reasoning_effort"),
        "detach": False, "wait": True,
    }
    return core.run_command_capture(getattr(core, f"command_worker_run_{operation}"), argparse.Namespace(**values))


def create_task(project: Path, task_id: str, *, resources: list[str] | None = None,
                sources: list[str] | None = None, process: str = "task-batch-execution") -> None:
    args = [
        "task-create", "--project-root", str(project), "--run", RUN_ID,
        "--id", task_id, "--title", task_id, "--process", process,
        "--execution-mode", "docs_only",
        "--allowed-file", f".pf/artifacts/{task_id}.md",
        "--required-output", f"id=report,path=.pf/artifacts/{task_id}.md",
        "--expected-report-artifact", f".pf/artifacts/{task_id}.md",
    ]
    for resource in resources or []:
        args.extend(["--workspace-knowledge-resource", resource])
    for source in sources or []:
        args.extend(["--required-source", source, "--allowed-read-file", source])
    pf(*args, "--apply")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def prepared_paths(project: Path, task: str) -> tuple[dict[str, Path], dict[str, Any], dict[str, Any]]:
    task_doc = core.load_task(project, task)
    paths = core.worker_run_paths(project, RUN_ID, task)
    state = read_json(paths["status"])
    manifest_path = project / state["prepared_input"]["path"]
    return paths, state, read_json(manifest_path)


def schema_check(document: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8-sig"))
    errors = core.validate_update_instance_against_schema(document, schema, schema, "$")
    require(not errors, {"schema_errors": errors})
    encoded = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    require(len(encoded) <= 4 * 1024 * 1024, {"manifest_bytes": len(encoded)})


def make_shell_driver(project: Path) -> Path:
    driver = copy.deepcopy(core.default_runtime_driver_documents()["generic-shell"])
    driver["id"] = "prepared-offline-fixture"
    driver["security"]["require_explicit_executable"] = False
    driver["environment"]["inherit"] = False
    driver["command"] = {
        "executable": "{python_executable}",
        "args": ["-c", (
            "import hashlib,json,os,pathlib,socket; "
            "socket.socket=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('socket disabled in fixture')); "
            "assert not any(k.startswith('PF_MCP') for k in os.environ); "
            "p=pathlib.Path(os.environ['PF_PREPARED_INPUT_FILE']); "
            "raw=p.read_bytes(); assert 'sha256:'+hashlib.sha256(raw).hexdigest()==os.environ['PF_PREPARED_INPUT_SHA256']; "
            "d=json.loads(raw); "
            "out=pathlib.Path(d['project_root'])/d['input']['outputs']['expected_report']['artifact']; "
            "out.parent.mkdir(parents=True,exist_ok=True); out.write_text('# Offline prepared execution\\n',encoding='utf-8')"
        )],
        "model_args": [],
    }
    path = project / ".pf" / "runtime" / "prepared-offline-driver.yaml"
    core.write_yaml_file(path, driver)
    return path


def event_rows(project: Path) -> list[dict[str, Any]]:
    path = core.event_runtime_paths(project)[0]
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def mutate_resource_indexing(workplace: Path, package: str, resource_id: str, mode: str) -> Path:
    import yaml

    path = workplace / "packages" / package / "package.yaml"
    package_doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    resource = next(row for row in package_doc["resources"] if row.get("id") == resource_id)
    if mode == "fulltext":
        resource["indexing"] = {"enabled": True, "mode": "fulltext", "fields": ["title", "description", "path"],
                                "sources": [{"path": ".", "mode": "fulltext", "include": ["**/*.md"]}]}
    else:
        resource["indexing"] = {"enabled": True, "mode": "metadata", "fields": ["title", "description", "path"],
                                "sources": [{"path": ".", "mode": "metadata", "role": "fixture_navigation"}]}
    path.write_text(yaml.safe_dump(package_doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-prepared-context-") as raw_root:
        temp_root = Path(raw_root)
        workplace, project = setup_basic_project(temp_root, "prepared-project")

        full_package, meta_package = "prepared-full", "prepared-meta"
        full_id = register_fixture_resource(workplace, full_package, "docs", {"guide.md": "PreparedFulltextMarker"}, title="Prepared Fulltext")
        full_resource = workplace / "packages" / full_package / "resources" / "docs" / "guide.md"
        full_original = full_resource.read_text(encoding="utf-8")
        mutate_resource_indexing(workplace, full_package, "docs", "fulltext")
        meta_id = register_fixture_resource(workplace, meta_package, "symbols", {"index.md": "MetadataBodyMustNotBeDelivered"}, title="Prepared Metadata Navigation")
        meta_resource = workplace / "packages" / meta_package / "resources" / "symbols" / "index.md"
        meta_original = meta_resource.read_text(encoding="utf-8")
        mutate_resource_indexing(workplace, meta_package, "symbols", "metadata")
        select_fixture_resource(project, workplace, full_package, "docs")
        select_fixture_resource(project, workplace, meta_package, "symbols")

        pf("run-create", "--project-root", str(project), "--id", RUN_ID, "--title", "Prepared regression", "--process", "task-batch-execution", "--apply")
        create_task(project, "empty-task")
        create_task(project, "unknown-grant-task", resources=["not-authorized-resource"])
        source_paths = [
            ".pf/artifacts/inputs/00-large.txt",
            ".pf/artifacts/inputs/10-a.txt",
            ".pf/artifacts/inputs/10-b.txt",
            ".pf/artifacts/inputs/10-c.txt",
            ".pf/artifacts/inputs/10-d.txt",
        ]
        sizes = [65537, 65536, 65536, 65536, 65536]
        for relative, size in zip(source_paths, sizes):
            target = project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("x" * size, encoding="utf-8")
        create_task(project, "source-task", sources=source_paths)
        create_task(project, "shell-task")
        create_task(project, "manual-task")
        create_task(project, "intent-task")
        create_task(project, "resource-task", resources=[full_id, meta_id])

        empty_status, empty_text = call(project, "unknown-grant-task", "prepare")
        require(empty_status != 0 and "resource_not_in_snapshot" in empty_text,
                {"status": empty_status, "output": empty_text})
        require(not core.worker_run_paths(project, RUN_ID, "unknown-grant-task")["status"].exists(),
                "unmatched resource grant left a ready worker state")

        status, output = call(project, "empty-task", "prepare")
        require(status == 0, output)
        _, _, empty_doc = prepared_paths(project, "empty-task")
        schema_check(empty_doc)
        import codex_exec_worker
        mutable_prompt = project / ".pf" / "runs" / RUN_ID / "worker-prompts" / "empty-task.md"
        mutable_capsule = core.assignment_capsule_path(project, "empty-task")
        mutable_workspace = project / ".pf" / "runtime" / "workspace-access.yaml"
        mutable_prompt.parent.mkdir(parents=True, exist_ok=True)
        mutable_workspace.parent.mkdir(parents=True, exist_ok=True)
        mutable_prompt.write_text("prompt before", encoding="utf-8")
        mutable_workspace.write_text("workspace before", encoding="utf-8")
        supplied_before = codex_exec_worker.prompt_payload(mutable_prompt, mutable_capsule, mutable_workspace, empty_doc)
        mutable_prompt.write_text("tampered prompt", encoding="utf-8")
        mutable_capsule.unlink(missing_ok=True)
        mutable_workspace.unlink(missing_ok=True)
        supplied_after = codex_exec_worker.prompt_payload(mutable_prompt, mutable_capsule, mutable_workspace, empty_doc)
        require(supplied_before == supplied_after and "tampered prompt" not in supplied_after,
                "prepared Codex payload depended on mutable prompt, capsule, or workspace pointer")
        empty_access = empty_doc["input"]["resources"]
        require(all(not empty_access["requested"][key] and not empty_access["grants"][key]
                    for key in ("knowledge_resources", "templates", "tools", "mcp")), empty_access)

        status, output = call(project, "source-task", "prepare")
        require(status == 0, output)
        source_paths_map, source_state, source_doc = prepared_paths(project, "source-task")
        schema_check(source_doc)
        sources = {item["path"]: item for item in source_doc["input"]["sources"] if item["path"] in source_paths}
        require(set(sources) == set(source_paths), sources)
        inline_total = sum(item.get("inline_bytes", 0) for item in source_doc["input"]["sources"])
        require(inline_total == 256 * 1024 and max(item.get("inline_bytes", 0) for item in sources.values()) == 64 * 1024,
                {"inline_total": inline_total, "sources": sources})
        require(sources[source_paths[0]]["truncated"] is True and sources[source_paths[0]]["inline_bytes"] == 65536
                and sources[source_paths[-1]]["delivery"] == "reference" and sources[source_paths[-1]]["inline_bytes"] == 0,
                sources)
        original_semantic = source_doc["input_fingerprint"]
        driver_path = make_shell_driver(project)
        status, output = call(project, "source-task", "prepare", driver=str(driver_path), model="offline-model", reasoning_effort="low")
        require(status == 0, output)
        _, switched_state, switched_doc = prepared_paths(project, "source-task")
        schema_check(switched_doc)
        require(switched_doc["input_fingerprint"] == original_semantic and switched_state["attempt"] == source_state["attempt"] + 1,
                {"first": source_state["attempt"], "second": switched_state["attempt"],
                 "before": original_semantic, "after": switched_doc["input_fingerprint"]})
        source_file = project / source_paths[0]
        source_bytes = source_file.read_bytes()
        source_file.write_bytes(source_bytes + b"changed")
        status, output = call(project, "source-task", "start")
        require(status != 0 and "required_source_changed" in output,
                {"status": status, "output": output})
        require(read_json(source_paths_map["status"])["status"] == "blocked", "changed source did not block prepared launch")
        source_file.write_bytes(source_bytes)

        status, output = call(project, "intent-task", "prepare")
        require(status == 0, output)
        original_task = copy.deepcopy(core.load_task(project, "intent-task"))
        changed_task = copy.deepcopy(original_task)
        changed_task["objective"] = str(changed_task.get("objective") or "") + " changed"
        core.save_task(project, changed_task)
        status, output = call(project, "intent-task", "start")
        require(status != 0 and "assignment_contract_changed" in output,
                {"status": status, "output": output})
        core.save_task(project, original_task)

        status, output = call(project, "shell-task", "prepare", driver=str(driver_path))
        require(status == 0, output)
        shell_paths, shell_state_1, shell_doc_1 = prepared_paths(project, "shell-task")
        schema_check(shell_doc_1)
        attempt1_manifest = project / shell_state_1["prepared_input"]["path"]
        original_manifest = attempt1_manifest.read_bytes()
        attempt1_manifest.write_bytes(original_manifest + b" ")
        status, output = call(project, "shell-task", "start")
        require(status != 0 and "prepared_input_checksum_mismatch" in output,
                {"status": status, "output": output})
        state_blocked = read_json(shell_paths["status"])
        require(state_blocked["status"] == "blocked" and state_blocked["attempt"] == shell_state_1["attempt"], state_blocked)
        require(not (project / ".pf" / "artifacts" / "shell-task.md").exists(), "tampered manifest reached the executor")
        status, output = call(project, "shell-task", "start")
        require(status != 0 and "explicit worker-run prepare" in output, {"status": status, "output": output})
        require(read_json(shell_paths["status"])["attempt"] == shell_state_1["attempt"], "blocked start implicitly created a new attempt")
        status, output = call(project, "shell-task", "prepare", driver=str(driver_path))
        require(status == 0, output)
        shell_paths, shell_state_2, shell_doc_2 = prepared_paths(project, "shell-task")
        schema_check(shell_doc_2)
        require(shell_state_2["attempt"] == shell_state_1["attempt"] + 1 and attempt1_manifest.read_bytes() == original_manifest + b" ",
                {"old_attempt": shell_state_1["attempt"], "new_attempt": shell_state_2["attempt"]})
        status, output = call(project, "shell-task", "start")
        require(status == 0 and "COMPLETED" in output, {"status": status, "output": output})
        completed = read_json(shell_paths["status"])
        require(completed["attempt"] == shell_state_2["attempt"] and completed["status"] == "completed"
                and completed["exit_code"] == 0 and read_json(shell_paths["heartbeat"])["status"] == "completed",
                completed)
        report_path = project / ".pf" / "artifacts" / "shell-task.md"
        require(report_path.is_file(), "offline executor did not produce the declared report")

        status, output = call(project, "manual-task", "prepare")
        require(status == 0, output)
        manual_paths, manual_state, manual_doc = prepared_paths(project, "manual-task")
        schema_check(manual_doc)
        manual_input = project / manual_state["prepared_input"]["path"]
        receipt_path = manual_input.with_name("collection-receipt.json")
        completion_path = manual_input.with_name("collection-complete.json")
        report_path_manual = project / ".pf" / "artifacts" / "manual-task.md"
        report_path_manual.parent.mkdir(parents=True, exist_ok=True)
        report_path_manual.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
        status, output = call(project, "manual-task", "collect")
        require(status != 0 and not receipt_path.exists(), {"status": status, "output": output, "receipt": receipt_path.exists()})
        report_path_manual.write_bytes(b"\xff invalid utf-8")
        status, output = call(project, "manual-task", "collect")
        require(status != 0 and not receipt_path.exists(), {"status": status, "output": output, "receipt": receipt_path.exists()})
        report_path_manual.write_text("# Manual prepared report\n", encoding="utf-8")

        assignment_path = core.assignment_yaml_path(project, "manual-task")
        run_path = core.run_root(project, RUN_ID) / "run.yaml"
        assignment_before = assignment_path.read_bytes()
        run_before = run_path.read_bytes()

        # A failed atomic publication must leave no partial receipt behind.
        import processforge_core.prepared_input as prepared_module
        original_link = prepared_module.os.link
        prepared_module.os.link = lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("injected link failure"))
        try:
            status, output = call(project, "manual-task", "collect")
        finally:
            prepared_module.os.link = original_link
        require(status != 0 and not receipt_path.exists(),
                {"status": status, "output": output, "partial_receipt": receipt_path.exists()})

        original_write_once = prepared_module.write_once
        def interrupt_completion(path: Path, document: dict[str, Any]) -> str:
            if path.name == "collection-complete.json":
                raise OSError("simulated completion interruption")
            return original_write_once(path, document)
        prepared_module.write_once = interrupt_completion
        try:
            try:
                status, output = call(project, "manual-task", "collect")
            except OSError as exc:
                status, output = 1, str(exc)
        finally:
            prepared_module.write_once = original_write_once
        require(status != 0 and receipt_path.is_file() and not completion_path.exists(),
                {"status": status, "output": output, "receipt": receipt_path.exists(), "completion": completion_path.exists()})
        status, output = call(project, "manual-task", "collect")
        require(status == 0 and completion_path.is_file(), {"status": status, "output": output})
        status, output = call(project, "manual-task", "collect")
        require(status == 0, {"status": status, "output": output})
        manual_events = event_rows(project)
        for event_type, expected_count in (("worker.run.collected", 1), ("task.completed", 1), ("assignment.completed", 1)):
            require(sum(row.get("event_type") == event_type for row in manual_events) == expected_count,
                    {"event_type": event_type, "events": manual_events})
        require(assignment_path.read_bytes() != assignment_before or run_path.read_bytes() != run_before,
                "legacy collection did not perform its compatibility completion transition")
        report_path_manual.write_text("# Mutated after collection\n", encoding="utf-8")
        status, output = call(project, "manual-task", "collect")
        require(status != 0 and "collected_output_changed" in output, {"status": status, "output": output})
        status, output = call(project, "manual-task", "prepare")
        require(status == 0, output)
        _, retry_state, retry_doc = prepared_paths(project, "manual-task")
        schema_check(retry_doc)
        retry_receipt = (project / retry_state["prepared_input"]["path"]).with_name("collection-receipt.json")
        status, output = call(project, "manual-task", "collect")
        require(status != 0 and "output_not_attributable_to_attempt" in output and not retry_receipt.exists(),
                {"status": status, "output": output})

        status, output = call(project, "resource-task", "prepare")
        require(status == 0, output)
        _, resource_state, resource_doc = prepared_paths(project, "resource-task")
        schema_check(resource_doc)
        grants = {item["id"]: item for item in resource_doc["input"]["resources"]["grants"]["knowledge_resources"]}
        require(full_id in grants and meta_id in grants, grants)
        require(grants[full_id]["material_kind"] == "fulltext" and grants[full_id]["resolution"]["status"] == "resolved"
                and "path" in grants[full_id]["resolution"], grants[full_id])
        require(grants[meta_id]["material_kind"] == "metadata" and grants[meta_id]["resolution"] == {"status": "metadata_only"}
                and "path" not in grants[meta_id]["resolution"] and "MetadataBodyMustNotBeDelivered" not in json.dumps(resource_doc),
                grants[meta_id])

        meta_resource.write_text("Changed metadata-only body", encoding="utf-8")
        pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace), "--apply")
        status, output = call(project, "resource-task", "start")
        require(status == 0 and "MANUAL" in output, {"status": status, "output": output})
        meta_resource.write_text(meta_original, encoding="utf-8")
        pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace), "--apply")

        full_resource.write_text("Changed fulltext body", encoding="utf-8")
        pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace), "--apply")
        status, output = call(project, "resource-task", "start")
        require(status != 0 and ("resource_material_changed" in output or "resource_generation_changed" in output),
                {"status": status, "output": output})
        full_resource.write_text(full_original, encoding="utf-8")
        pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace), "--apply")

        import yaml
        project_manifest_path = project / ".pf" / "process-forge.yaml"
        original_project_manifest = project_manifest_path.read_bytes()
        manifest_doc = yaml.safe_load(original_project_manifest)
        resources_requirement = manifest_doc["context_requirements"]["knowledge_resources"]
        manifest_doc["context_requirements"]["knowledge_resources"] = [item for item in resources_requirement
                                                                           if item.get("id") not in {"docs", "symbols"}]
        project_manifest_path.write_text(yaml.safe_dump(manifest_doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace), "--apply")
        status, output = call(project, "resource-task", "prepare")
        require(status != 0 and ("resource_access_revoked" in output or "resource_not_selected" in output),
                {"status": status, "output": output})
        project_manifest_path.write_bytes(original_project_manifest)
        pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace), "--apply")

        empty_process = copy.deepcopy(core.resolve_process_definition(project, "task-batch-execution").process)
        empty_process["id"] = "prepared-empty-subset"
        empty_process["name"] = "Prepared empty subset fixture"
        initial = empty_process["stages"][0]
        empty_process["initial_stage"] = initial["id"]
        initial["resource_subset"] = []
        empty_process_path = project / "processes" / "custom" / "prepared-empty-subset.yaml"
        core.write_yaml_file(empty_process_path, empty_process)
        pf("run-create", "--project-root", str(project), "--id", "prepared-subset-run", "--title", "Stage subset regression", "--process", "prepared-empty-subset", "--apply")
        subset_args = ["task-create", "--project-root", str(project), "--run", "prepared-subset-run", "--id", "empty-subset-task",
                       "--title", "empty-subset-task", "--process", "prepared-empty-subset", "--stage", initial["id"], "--execution-mode", "docs_only",
                       "--workspace-knowledge-resource", full_id, "--allowed-file", ".pf/artifacts/empty-subset-task.md",
                       "--required-output", "id=report,path=.pf/artifacts/empty-subset-task.md",
                       "--expected-report-artifact", ".pf/artifacts/empty-subset-task.md", "--apply"]
        pf(*subset_args)
        status, output = call(project, "empty-subset-task", "prepare")
        require(status != 0 and "resource_not_in_stage" in output, {"status": status, "output": output})

        print("PASS: prepared-input schema/budgets, empty and denied grants, semantic driver/model invariance, source/intent/manifest drift denial, offline generic-shell same-attempt launch, receipt interruption repair/idempotent collection/output attribution, metadata/fulltext drift and revocation, explicit empty stage subset")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
