#!/usr/bin/env python3
"""Real Work lifecycle parity across optional diagnostics profiles."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from unittest.mock import patch

import yaml

from process_execution_smoke_support import assignment, event_types, fixture, run, state
from smoke_garage_mode_not_promoted_by_session import call_mcp, cli


PROFILES = ("quiet", "normal", "diagnostic", "trace", "off")
EVIDENCE_BYTES = b"stable process-invariance evidence\n"


def read_records(project: Path) -> list[dict]:
    root = project / ".pf" / "runtime" / "diagnostics"
    records = []
    for path in (root / "diagnostics.jsonl", *(root / f"diagnostics.{i}.jsonl" for i in range(1, 8))):
        if path.is_file():
            records.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return records


def normalized_history(task: dict) -> list[dict]:
    result = []
    for entry in task.get("stage_history", []):
        evidence = []
        for item in entry.get("evidence", []):
            evidence.append({key: item.get(key) for key in ("kind", "artifact_id", "gate_id", "status", "path", "sha256") if key in item})
        result.append({key: entry.get(key) for key in ("stage_id", "status", "outcome", "next_stage_id")} | {"evidence": evidence})
    return result


def process_semantics(task: dict) -> dict:
    execution = task.get("stage_execution") or {}
    return {"stage": task.get("stage"), "stage_status": task.get("stage_status"), "status": task.get("status"),
            "stage_history": task.get("stage_history", []), "evidence": execution.get("evidence") or [],
            "blockers": execution.get("blockers") or [], "blocked_at": execution.get("blocked_at")}


def evidence(artifact_id: str, gate_id: str, project: Path) -> list[dict[str, str]]:
    rel = Path(".pf") / "artifacts" / "process-invariance" / f"{artifact_id}.md"
    path = project / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(EVIDENCE_BYTES)
    digest = "sha256:" + hashlib.sha256(EVIDENCE_BYTES).hexdigest()
    return [
        {"kind": "artifact", "artifact_id": artifact_id, "status": "ready", "summary": f"{artifact_id} ready", "path": rel.as_posix(), "sha256": digest},
        {"kind": "gate", "gate_id": gate_id, "status": "passed", "summary": f"{gate_id} passed"},
    ]


def transition(workplace: Path, project: Path, artifact: str, gate: str) -> dict:
    result = call_mcp(workplace, "pf.work.transition", {"project_root": str(project), "outcome": "completed",
                       "evidence": evidence(artifact, gate, project), "notes": f"Complete {artifact}"})
    if result.get("action") not in {"stage_transitioned", "run_completed"}:
        raise AssertionError(result)
    return result


def scenario(profile: str) -> dict:
    with fixture() as (workplace, project, started):
        assignment_path = project / ".pf" / "assignments" / f"{started['assignment_id']}.yaml"
        capsule_path = project / ".pf" / "contexts" / "assignment-capsules" / f"{started['assignment_id']}.capsule.yaml"
        capsule_bytes = capsule_path.read_bytes()
        before_assignment = assignment_path.read_bytes()
        before_document = yaml.safe_load(before_assignment)
        before_semantics = process_semantics(before_document)
        before_events = event_types(project)
        before_records = Counter(json.dumps(record, sort_keys=True, ensure_ascii=False) for record in read_records(project))

        settings = {"schema_version": 1, "profile": profile, "sink": "jsonl"}
        if profile in {"diagnostic", "trace"}:
            settings["expires_at"] = datetime.fromtimestamp(time.time() + 8 * 60, timezone.utc).isoformat()
        config_path = project / ".pf" / "diagnostics.json"
        config_path.write_text(json.dumps(settings), encoding="utf-8")

        rejected = call_mcp(workplace, "pf.work.transition", {"project_root": str(project), "outcome": "completed"})
        after_rejection = assignment(project, started)
        nonsemantic_changes = sorted(key for key in set(before_document) | set(after_rejection)
                                     if key not in {"stage", "stage_status", "status", "stage_history", "stage_execution"}
                                     and before_document.get(key) != after_rejection.get(key))
        before_execution, after_execution = before_document.get("stage_execution") or {}, after_rejection.get("stage_execution") or {}
        nonsemantic_execution_changes = sorted(key for key in set(before_execution) | set(after_execution)
                                               if key not in {"evidence", "blockers", "blocked_at"}
                                               and before_execution.get(key) != after_execution.get(key))
        if (rejected.get("action") not in {"incomplete", "transition_rejected"}
                or process_semantics(after_rejection) != before_semantics or capsule_path.read_bytes() != capsule_bytes):
            raise AssertionError({"profile": profile, "negative": rejected,
                                  "semantic_assignment_preserved": process_semantics(after_rejection) == before_semantics,
                                  "capsule_preserved": capsule_path.read_bytes() == capsule_bytes})

        first = transition(workplace, project, "brief", "prepare-ready")
        if first.get("next_stage_id") != "build":
            raise AssertionError(first)
        second = transition(workplace, project, "change", "build-ready")
        if second.get("next_stage_id") != "verify":
            raise AssertionError(second)
        final = transition(workplace, project, "report", "verify-ready")
        task, run_data = assignment(project, started), run(project, started)
        if final.get("action") != "run_completed" or run_data.get("status") != "completed" or task.get("status") != "done":
            raise AssertionError({"profile": profile, "final": final, "run": run_data.get("status"), "task": task.get("status")})
        cli("project-context-check", "--project-root", str(project), "--workplace", str(workplace), "--json")
        if capsule_path.read_bytes() != capsule_bytes:
            raise AssertionError("pinned assignment capsule bytes changed")

        all_records = read_records(project)
        record_counts = Counter(json.dumps(record, sort_keys=True, ensure_ascii=False) for record in all_records)
        added = list((record_counts - before_records).elements())
        added_records = [json.loads(line) for line in added]
        events = event_types(project)[len(before_events):]
        return {"profile": profile, "history": normalized_history(task), "evidence_hashes": [item.get("sha256") for row in normalized_history(task) for item in row["evidence"] if item.get("sha256")],
                "status": (run_data.get("status"), task.get("status")), "events": events,
                "negative": (rejected.get("action"), rejected.get("reason")),
                "negative_nonsemantic_assignment_changes": nonsemantic_changes,
                "negative_nonsemantic_execution_changes": nonsemantic_execution_changes,
                "optional_records": added_records, "capsule_sha256": hashlib.sha256(capsule_bytes).hexdigest()}


def main() -> int:
    results = []
    with patch.dict(os.environ, {"PF_DIAGNOSTICS": ""}, clear=False):
        for profile in PROFILES:
            results.append(scenario(profile))
    reference = results[0]
    for result in results[1:]:
        for key in ("history", "evidence_hashes", "status", "events", "negative"):
            if result[key] != reference[key]:
                raise AssertionError({"profile": result["profile"], "field": key, "expected": reference[key], "actual": result[key]})
    counts = {item["profile"]: len(item["optional_records"]) for item in results}
    if counts["off"] != 0 or counts["diagnostic"] <= counts["normal"] or counts["trace"] <= counts["diagnostic"]:
        raise AssertionError({"optional_record_counts": counts})
    if not any(record.get("code") == "context.check.span_start" for record in results[-2]["optional_records"]):
        raise AssertionError("trace profile did not add trace span detail")
    print("PASS: Work lifecycle invariant across diagnostic profiles " + json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
