"""Project refresh must remain independent of workplace index maintenance."""

from __future__ import annotations

import argparse
import ast
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


def _refresh_command(namespace: dict[str, Any]) -> Any:
    """Load only the real command, isolating unrelated legacy assembly effects."""
    source = Path(__file__).resolve().parents[2] / "tools" / "processforge.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "command_project_context_refresh"
    )
    exec(
        compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"),
        namespace,
    )
    return namespace["command_project_context_refresh"]


def _scenario(
    tmp_path: Path,
    *,
    search_status: str,
    required_status: str = "ready",
    dry_run: bool = False,
) -> tuple[int, dict[str, int], str]:
    project = tmp_path / "project"
    workplace = tmp_path / "workplace"
    project.mkdir(exist_ok=True)
    workplace.mkdir(exist_ok=True)
    database = workplace / "existing-index.sqlite"
    database.write_bytes(b"existing index bytes stay unchanged")
    previous = database.read_bytes()
    counts = {"snapshot_write": 0, "observation": 0, "maintenance": 0}
    snapshot = {
        "snapshot": {"id": "new-generation", "health": {"status": "pass"}},
        "resource_readiness": {"status": required_status},
        "capabilities": {"required": [], "optional": []},
    }

    def snapshot_write(*_args: Any, **_kwargs: Any) -> tuple[Any, ...]:
        counts["snapshot_write"] += 1
        return "fresh", {"snapshot_yaml": project / "snapshot.yaml"}, snapshot, []

    def observe(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        counts["observation"] += 1
        return {
            "schema_version": 1,
            "kind": "pf.search_index.maintenance",
            "scope": "workplace",
            "results": [{"action": "none", "search_status": search_status}],
        }

    def forbidden_maintenance(*_args: Any, **_kwargs: Any) -> Any:
        counts["maintenance"] += 1
        raise AssertionError("project refresh attempted workplace indexing")

    def no_effect(*_args: Any, **_kwargs: Any) -> None:
        return None

    namespace = {
        "argparse": argparse,
        "Path": Path,
        "Any": Any,
        "_run_task_inputs": SimpleNamespace(require_flow_root=no_effect),
        "build_project_context_snapshot": lambda *_a, **_k: snapshot,
        "project_context_check_result": lambda *_a, **_k: {
            "snapshot_id": "previous-generation",
            "status": "missing",
        },
        "write_project_context_snapshot_outputs": snapshot_write,
        "dump_yaml": lambda value: json.dumps(value) + "\n",
        "_core_common_clock": SimpleNamespace(now_utc=lambda: "2026-10-23T00:00:00Z"),
        "_telemetry_event_service": SimpleNamespace(
            telemetry_session_id=lambda *_a: "fixture-session",
            append_telemetry_event=no_effect,
        ),
        "_session_metadata_writer": SimpleNamespace(
            session_runtime_paths=lambda *_a: (
                project / "session.json",
                project / "telemetry.jsonl",
            )
        ),
        "_process_event_recorder": SimpleNamespace(emit_process_event=no_effect),
        "_project_coordination_state": SimpleNamespace(
            resolve_project_workplace_manifest=lambda *_a: workplace / "workplace.yaml"
        ),
        "rel": lambda path, _root: path.name,
        "search_index_maintenance_for_known_projects": forbidden_maintenance,
        "observe_search_index_for_project": observe,
        "print_search_index_maintenance_summary": lambda payload: print(
            "SEARCH_INDEX:", payload["results"][0]["search_status"]
        ),
    }
    command = _refresh_command(namespace)
    output = io.StringIO()
    with redirect_stdout(output):
        result = command(
            argparse.Namespace(
                project_root=str(project),
                workplace=str(workplace),
                dry_run=dry_run,
                reason="fixture",
                write_proposal=None,
            )
        )
    assert database.read_bytes() == previous
    return result, counts, output.getvalue()


@pytest.mark.parametrize(
    "search_status", ["missing", "stale", "building", "degraded", "fresh"]
)
def test_refresh_observes_without_indexing(tmp_path: Path, search_status: str) -> None:
    result, counts, output = _scenario(tmp_path, search_status=search_status)
    assert result == 0
    assert counts == {"snapshot_write": 1, "observation": 1, "maintenance": 0}
    assert "STATUS: fresh" in output
    assert f"SEARCH_INDEX: {search_status}" in output


def test_search_availability_does_not_weaken_required_resources(tmp_path: Path) -> None:
    result, counts, _output = _scenario(
        tmp_path, search_status="fresh", required_status="blocked"
    )
    assert result == 1
    assert counts["maintenance"] == 0


def test_repeated_refresh_never_requests_maintenance(tmp_path: Path) -> None:
    for _attempt in range(2):
        result, counts, _output = _scenario(tmp_path, search_status="stale")
        assert result == 0
        assert counts["maintenance"] == 0


def test_dry_run_does_not_touch_search_or_write_snapshot(tmp_path: Path) -> None:
    result, counts, output = _scenario(tmp_path, search_status="missing", dry_run=True)
    assert result == 0
    assert counts == {"snapshot_write": 0, "observation": 0, "maintenance": 0}
    assert json.loads(output)["after"]["status"] == "fresh"
