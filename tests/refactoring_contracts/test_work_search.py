"""Exercise ordinary Work and version-scoped search through the selected Core."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

PACKAGE = "fixture.search-versions"
RESOURCE = f"{PACKAGE}:guide"
MCP_ENTRY = "tools/pf_runtime/mcp_server.py"


def cli(distribution: Any, *args: str | Path) -> str:
    result = distribution.run(*args)
    assert result.returncode == 0, (result.stdout, result.stderr)
    return result.stdout


def calls(
    distribution: Any,
    workplace: Path,
    project: Path,
    *requests: tuple[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    frames = [{"jsonrpc": "2.0", "id": 0, "method": "initialize"}]
    for number, (tool, arguments) in enumerate(requests, 1):
        frames.append(
            {
                "jsonrpc": "2.0",
                "id": number,
                "method": "tools/call",
                "params": {
                    "name": tool,
                    "arguments": {"project_root": str(project), **arguments},
                },
            }
        )
    result = distribution.run(
        "--workplace",
        workplace,
        entry=MCP_ENTRY,
        input_text="".join(json.dumps(frame) + "\n" for frame in frames),
    )
    assert result.returncode == 0 and result.stderr == "", result
    replies = [json.loads(line) for line in result.stdout.splitlines()]
    assert [reply["id"] for reply in replies] == list(range(len(frames))), replies
    assert all(reply["jsonrpc"] == "2.0" and "error" not in reply for reply in replies)
    assert "result" in replies[0]
    payloads = []
    for reply in replies[1:]:
        envelope = reply["result"]
        assert not envelope.get("isError"), envelope
        payload = json.loads(envelope["content"][0]["text"])
        if "structuredContent" in envelope:
            assert envelope["structuredContent"] == payload
        payloads.append(payload)
    return payloads


def declarative_process(distribution: Any) -> dict[str, Any]:
    # Reuse the selected target's smoke definition in its own isolated interpreter.
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            "import json, sys; sys.path.insert(0, 'tools'); "
            "from process_execution_smoke_support import PROCESS; "
            "print(json.dumps(PROCESS))",
        ],
        cwd=distribution.root,
        env=distribution.environment,
        capture_output=True,
        encoding="utf-8",
        timeout=120,
        check=True,
    )
    process = json.loads(result.stdout)
    process["stages"][0]["resource_subset"] = [RESOURCE]
    return process


def seed_versions(workplace: Path) -> list[Path]:
    # Same discriminating corpus as smoke_workplace_search_index.
    package = workplace / "packages" / PACKAGE
    roots, resources = [], []
    for number in (1, 2):
        version = f"{number}.0.0"
        root = package / version
        root.mkdir(parents=True)
        for name in ("one.md", "two.md"):
            (root / name).write_text(
                f"sharedmatch uniquematch{number}", encoding="utf-8"
            )
        roots.append(root)
        resources.append(
            {
                "id": "guide",
                "kind": "documentation",
                "title": "Versioned Guide",
                "version": version,
                "path": version,
                "indexing": {
                    "mode": "fulltext",
                    "sources": [
                        {"path": ".", "mode": "fulltext", "include": ["**/*.md"]}
                    ],
                },
            }
        )
    (roots[1] / "filler.md").write_text("unselectedfiller", encoding="utf-8")
    (package / "package.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "id": PACKAGE,
                "version": "1.0.0",
                "kind": "documentation",
                "resources": resources,
            }
        ),
        encoding="utf-8",
    )
    return roots


def onboard(
    distribution: Any, workplace: Path, project: Path, version: str, process: dict
) -> None:
    project.mkdir()
    cli(
        distribution,
        "project-onboard",
        "--project-root",
        project,
        "--workplace",
        workplace,
        "--type",
        "generic",
        "--coordination-mode",
        "simple",
        "--apply",
    )
    process_path = project / "processes/custom/declarative-smoke.yaml"
    process_path.parent.mkdir(parents=True)
    process_path.write_text(yaml.safe_dump(process), encoding="utf-8")
    manifest_path = project / ".pf/process-forge.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["process"] = process["id"]
    manifest["knowledge_stack"].append(
        {"id": PACKAGE, "version": "1.0.0", "source": "workplace"}
    )
    requirements = manifest["context_requirements"]
    requirements["knowledge_packages"].append(
        {"id": PACKAGE, "constraint": "*", "required": True}
    )
    requirements["knowledge_resources"] = [
        {"id": RESOURCE, "preferred_version": version, "required": True}
    ]
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    cli(
        distribution,
        "project-context-refresh",
        "--project-root",
        project,
        "--workplace",
        workplace,
        "--apply",
    )


def start(distribution: Any, workplace: Path, project: Path) -> dict[str, str]:
    (started,) = calls(
        distribution,
        workplace,
        project,
        ("pf.work.start", {"objective": f"Check ordinary Work in {project.name}"}),
    )
    assert started["action"] == "created_new" and started["stage"] == "prepare", started
    return {
        "run_id": started["run_id"],
        "assignment_id": started["assignment_id"],
        "context_id": started["context"]["id"],
    }


def work_documents(
    project: Path, selectors: dict[str, str]
) -> tuple[dict, dict, bytes, list[tuple[str, str]]]:
    flow = project / ".pf"
    assignment_id = selectors["assignment_id"]
    assignment = yaml.safe_load(
        (flow / "assignments" / f"{assignment_id}.yaml").read_bytes()
    )
    run = yaml.safe_load(
        (flow / "runs" / selectors["run_id"] / "run.yaml").read_bytes()
    )
    capsule = (
        flow / "contexts/assignment-capsules" / f"{assignment_id}.capsule.yaml"
    ).read_bytes()
    uri = (flow / "runtime/events/events.sqlite3").resolve().as_uri()
    with closing(sqlite3.connect(uri + "?mode=ro", uri=True)) as database:
        events = database.execute(
            "SELECT event_type, event_id FROM events ORDER BY seq"
        ).fetchall()
    return assignment, run, capsule, events


def assert_work_state(payload: dict, selectors: dict[str, str], stage: str) -> None:
    assert payload["run"]["id"] == selectors["run_id"], payload
    assert payload["assignment"]["id"] == selectors["assignment_id"], payload
    assert payload["context"]["id"] == selectors["context_id"], payload
    assert payload["stage"]["id"] == stage, payload


def transition_request(
    selectors: dict[str, str], artifact: str, gate: str
) -> dict[str, Any]:
    return {
        **selectors,
        "outcome": "completed",
        "evidence": [
            {"kind": "artifact", "artifact_id": artifact, "status": "ready"},
            {"kind": "gate", "gate_id": gate, "status": "passed"},
        ],
    }


def check_transition(
    distribution: Any,
    workplace: Path,
    project: Path,
    selectors: dict[str, str],
    sibling: Path,
    other: dict[str, str],
) -> None:
    before = work_documents(project, selectors)
    sibling_before = work_documents(sibling, other)
    (state,) = calls(distribution, workplace, project, ("pf.work.state", selectors))
    assert_work_state(state, selectors, "prepare")
    transition = transition_request(selectors, "brief", "prepare-ready")
    invalid = {**selectors, "context_id": other["context_id"]}
    denied_state, denied_transition, denied_search = calls(
        distribution,
        workplace,
        project,
        ("pf.work.state", invalid),
        ("pf.work.transition", {**transition, **invalid}),
        ("pf.work.search", {**invalid, "query": "sharedmatch"}),
    )
    for denial in (denied_state, denied_transition):
        assert denial["action"] == "blocked", denial
        assert denial["reason"] == "work_context_mismatch", denial
    assert denied_search["status"] == "blocked", denied_search
    assert denied_search["reason"] == "work_context_mismatch", denied_search
    assert work_documents(project, selectors) == before
    assert work_documents(sibling, other) == sibling_before

    (advanced,) = calls(
        distribution, workplace, project, ("pf.work.transition", transition)
    )
    assert advanced["action"] == "stage_transitioned", advanced
    assert advanced["previous_stage_id"] == "prepare", advanced
    assert advanced["next_stage_id"] == "build", advanced
    assert_work_state(advanced, selectors, "build")

    assignment, _, capsule, events = work_documents(project, selectors)
    (history,) = assignment["stage_history"]
    assert history["stage_id"] == "prepare" and history["next_stage_id"] == "build"
    assert len(history["evidence"]) == 2
    assert assignment["stage_execution"]["evidence"] == []
    assert capsule == before[2]
    assert events[: len(before[3])] == before[3]
    assert [event_type for event_type, _ in events[len(before[3]) :]] == [
        "process.stage.completed",
        "process.stage.transitioned",
        "process.stage.started",
    ]
    assert len({event_id for _, event_id in events}) == len(events)

    (build,) = calls(
        distribution,
        workplace,
        project,
        ("pf.work.transition", transition_request(selectors, "change", "build-ready")),
    )
    assert build["action"] == "stage_transitioned", build
    assert build["next_stage_id"] == "verify", build
    final_request = transition_request(selectors, "report", "verify-ready")
    (finished,) = calls(
        distribution, workplace, project, ("pf.work.transition", final_request)
    )
    assert finished["action"] == "run_completed", finished
    assert_work_state(finished, selectors, "verify")
    terminal = work_documents(project, selectors)
    assert terminal[1]["status"] == "completed"
    assert [item["stage_id"] for item in terminal[0]["stage_history"]] == [
        "prepare",
        "build",
        "verify",
    ]
    assert [len(item["evidence"]) for item in terminal[0]["stage_history"]] == [2, 2, 2]
    assert terminal[2] == before[2]
    assert terminal[3][: len(events)] == events
    assert len({event_id for _, event_id in terminal[3]}) == len(terminal[3])

    # Replay confirmed terminal completion. Unknown transport outcomes are never retried.
    replay, state = calls(
        distribution,
        workplace,
        project,
        ("pf.work.transition", final_request),
        ("pf.work.state", selectors),
    )
    assert replay["action"] == "blocked", replay
    assert replay["reason"] == "work_is_terminal", replay
    assert_work_state(state, selectors, "verify")
    assert work_documents(project, selectors) == terminal
    assert work_documents(sibling, other) == sibling_before
    (sibling_state,) = calls(distribution, workplace, sibling, ("pf.work.state", other))
    assert_work_state(sibling_state, other, "prepare")


def check_search(
    distribution: Any,
    workplace: Path,
    project: Path,
    root: Path,
    selectors: dict[str, str],
    number: int,
) -> None:
    own_marker = f"uniquematch{number}"
    other_marker = f"uniquematch{3 - number}"
    first, second, own, other, resolved, work, excluded, material = calls(
        distribution,
        workplace,
        project,
        ("pf.search", {"query": "sharedmatch", "limit": 1}),
        ("pf.search", {"query": "sharedmatch", "limit": 1, "offset": 1}),
        ("pf.search", {"query": own_marker}),
        ("pf.search", {"query": other_marker}),
        ("pf.resolve", {"resource_id": RESOURCE}),
        ("pf.work.search", {**selectors, "query": own_marker, "limit": 1}),
        ("pf.work.search", {**selectors, "query": other_marker}),
        ("pf.work.resolve", {**selectors, "resource_id": RESOURCE}),
    )
    assert Path(resolved["resource"]["local_root"]) == root.resolve(), resolved
    assert own["total"] == 2, own
    assert first["page"]["next_limitstart"] == 1, first
    assert all(
        response["scope"] == "project_context" and response["search_status"] == "fresh"
        for response in (first, second, own, other)
    )
    if distribution.profile == "published-1.3.0":
        # #120: the original index query admitted both instances of the logical ID.
        assert first["total"] == second["total"] == 4, (first, second)
        assert first["page"]["total"] == second["page"]["total"] == 4
        assert second["page"]["next_limitstart"] == 2, second
        assert other["total"] == 2, other
        for response, version in ((own, root.name), (other, f"{3 - number}.0.0")):
            assert {row["metadata"]["version"] for row in response["results"]} == {
                version
            }
    else:
        assert other["total"] == 0 and other["results"] == [], other
        assert second["page"]["next_limitstart"] is None, second
        expected_document_count = 2 if number == 1 else 3
        assert own["authorized_coverage"]["document_count"] == expected_document_count
        root_id = hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()
        for response, name in ((first, "one.md"), (second, "two.md")):
            assert response["search_status"] == "fresh" and response["total"] == 2
            assert response["page"]["total"] == 2 and response["page"]["returned"] == 1
            (result,) = response["results"]
            metadata = result["metadata"]
            assert (
                result["resource_id"] == RESOURCE and result["canonical_path"] == name
            )
            assert metadata["version"] == root.name
            assert metadata["instance_id"] == f"{RESOURCE}@{root.name}"
            assert metadata["root_id"] == root_id
            local_file = Path(result["local_path"])
            assert local_file == (root / name).resolve()
            assert local_file.read_bytes() == f"sharedmatch {own_marker}".encode()

    assert work["total"] == 2 and excluded["total"] == 0
    assert excluded["results"] == []
    assert work["page"]["next_limitstart"] == 1
    for response in (work, excluded, material):
        assert response["status"] == "ready", response
        assert response["scope"] == "work_context"
        assert response["coverage"]["source"] == "verified_work_material"
        assert all(response["work"][key] == value for key, value in selectors.items())
    assert Path(material["resource"]["local_root"]) == root.resolve(), material
    assert material["resource"]["navigation"] == "verified_declared_material"
    (provenance,) = material["resource_provenance"]
    assert provenance["resource_id"] == RESOURCE
    assert provenance["material_kind"] == "fulltext"
    assert provenance["material_fingerprint"].startswith("sha256:")
    assert all(provenance[key] == value for key, value in selectors.items())
    assert provenance["generation"] == root.name
    assert work["results"][0]["resource_provenance"] == provenance
    assert (
        work["resource_provenance"] == excluded["resource_provenance"] == [provenance]
    )


def test_ordinary_work_and_search(contract_distribution: Any, tmp_path: Path) -> None:
    """Compare selected Work material with the project's shared physical index."""
    workplace = tmp_path / "workplace"
    cli(contract_distribution, "workplace-init", "--workplace", workplace, "--apply")
    roots = seed_versions(workplace)
    process = declarative_process(contract_distribution)
    projects = [tmp_path / "project-1", tmp_path / "project-2"]
    for project, root in zip(projects, roots, strict=True):
        onboard(contract_distribution, workplace, project, root.name, process)
    works = [start(contract_distribution, workplace, project) for project in projects]
    assert all(works[0][key] != works[1][key] for key in works[0])
    report = json.loads(
        cli(
            contract_distribution,
            "search-index-maintain",
            "--workplace",
            workplace,
            "--apply",
            "--json",
        )
    )
    assert report["scope"] == "workplace" and report["results"][0]["status"] == "ok"
    for number, (project, root, selectors) in enumerate(
        zip(projects, roots, works, strict=True), 1
    ):
        check_search(contract_distribution, workplace, project, root, selectors, number)
    check_transition(
        contract_distribution, workplace, projects[0], works[0], projects[1], works[1]
    )
