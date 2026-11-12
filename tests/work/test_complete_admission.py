"""Whole-Work completion admission with real file-only consumer fixtures."""

from __future__ import annotations

import copy
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import processforge as core
import pytest
import yaml
from process_execution_smoke_support import PROCESS, stage_evidence
from smoke_garage_mode_not_promoted_by_session import cli


def make_work(
    root: Path,
    *,
    final_retry: bool = False,
    verify_outcomes: list[dict[str, str]] | None = None,
):
    workplace, project = root / "workplace", root / "project"
    cli("workplace-init", "--workplace", str(workplace), "--apply")
    cli(
        "project-onboard",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--type",
        "generic",
        "--coordination-mode",
        "simple",
        "--apply",
    )
    process = copy.deepcopy(PROCESS)
    if final_retry:
        process["stages"][-1]["outcomes"] = [
            {"id": "completed", "next_stage": ""},
            {"id": "retry", "next_stage": "prepare"},
        ]
    if verify_outcomes is not None:
        process["stages"][-1]["outcomes"] = copy.deepcopy(verify_outcomes)
    path = project / "processes/custom/declarative-smoke.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(process, sort_keys=False), encoding="utf-8")
    manifest_path = project / ".pf/process-forge.yaml"
    manifest = yaml.safe_load(manifest_path.read_bytes())
    manifest["process"] = "declarative-smoke"
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    cli(
        "project-context-refresh",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--reason",
        "completion admission fixture",
        "--apply",
    )
    service = core.process_execution_service(project, str(workplace))
    started = service.start(
        objective="Complete only the whole Work",
        scope_intent={
            "schema_version": 1,
            "assignment": {
                "allowed_actions": ["read", "write_artifact", "write_product"],
                "allowed_files": ["**"],
                "allowed_read_files": ["**"],
                "execution_mode": {
                    "kind": "implementation",
                    "code_changes_allowed": True,
                    "artifact_changes_allowed": True,
                    "requires_review": False,
                },
                "ownership": {
                    "owner_id": "completion-fixture",
                    "role": "developer",
                    "writer": True,
                },
            },
        },
    )
    assert started["action"] == "created_new", started
    selection = {"run_id": started["run_id"], "assignment_id": started["assignment_id"]}
    state = service.state(**selection)
    assert state["context"]["validation"]["status"] == "valid", state
    assert state["execution_readiness"]["status"] == "ready", state
    return service, selection, project, workplace


def saved_work(project: Path) -> dict[str, bytes]:
    return {
        path.relative_to(project).as_posix(): path.read_bytes()
        for path in (project / ".pf").rglob("*")
        if path.is_file() and not path.name.endswith((".lock", ".guard"))
    }


def final_stage(service: Any, selection: dict[str, str]) -> None:
    for artifact, gate in [("brief", "prepare-ready"), ("change", "build-ready")]:
        result = service.transition(
            **selection, outcome="completed", evidence=stage_evidence(artifact, gate)
        )
        assert result["action"] == "stage_transitioned", result
    assert service.state(**selection)["stage"]["id"] == "verify"


def reason_codes(result: dict[str, Any]) -> set[str]:
    return {str(result.get("reason") or "")} | {
        str(item.get("code") or "") for item in result.get("blockers", [])
    }


@pytest.mark.parametrize("evidence_kind", ["absent", "valid", "malformed"])
def test_complete_nonfinal_is_read_only(tmp_path: Path, evidence_kind: str) -> None:
    service, selection, project, _workplace = make_work(tmp_path)
    readiness = service.can_complete(**selection)
    assert not readiness["can_complete"]
    assert "not_final_stage" in reason_codes(readiness)
    evidence = {
        "absent": None,
        "valid": stage_evidence("brief", "prepare-ready"),
        "malformed": [{"kind": "unsupported-kind"}],
    }[evidence_kind]
    before = saved_work(project)
    result = service.complete(**selection, evidence=evidence, notes="do not advance")
    assert result["action"] == "blocked", result
    assert "not_final_stage" in reason_codes(result)
    assert saved_work(project) == before
    assert service.state(**selection)["stage"]["id"] == "prepare"


def test_complete_final_accepts_incoming_evidence(tmp_path: Path) -> None:
    service, selection, _project, _workplace = make_work(tmp_path)
    final_stage(service, selection)
    result = service.complete(
        **selection,
        evidence=stage_evidence("report", "verify-ready"),
        notes="whole Work completed",
    )
    assert result["action"] == "run_completed", result


def test_complete_does_not_use_nonterminal_outcome(tmp_path: Path) -> None:
    service, selection, project, _workplace = make_work(tmp_path, final_retry=True)
    final_stage(service, selection)
    evidence = stage_evidence("report", "verify-ready")
    before = saved_work(project)
    result = service.complete(
        **selection, outcome="retry", evidence=evidence, notes="retry is not completion"
    )
    assert result["action"] == "blocked", result
    assert "not_terminal_outcome" in reason_codes(result)
    assert saved_work(project) == before
    ordinary = service.transition(**selection, outcome="retry", evidence=evidence)
    assert ordinary["action"] == "stage_transitioned", ordinary
    assert ordinary["stage"]["id"] == "prepare"


@pytest.mark.parametrize("terminal_first", [True, False])
def test_complete_uses_effective_duplicate_outcome(
    tmp_path: Path, terminal_first: bool
) -> None:
    terminal = {"id": "completed", "next_stage": ""}
    retry = {"id": "completed", "next_stage": "prepare"}
    outcomes = [terminal, retry] if terminal_first else [retry, terminal]
    service, selection, project, _workplace = make_work(
        tmp_path, verify_outcomes=outcomes
    )
    final_stage(service, selection)
    evidence = stage_evidence("report", "verify-ready")
    before = saved_work(project)
    result = service.complete(
        **selection, evidence=evidence, notes="effective duplicate outcome"
    )
    if terminal_first:
        assert result["action"] == "blocked", result
        assert "not_terminal_outcome" in reason_codes(result)
        assert saved_work(project) == before
        ordinary = service.transition(
            **selection, outcome="completed", evidence=evidence
        )
        assert ordinary["action"] == "stage_transitioned", ordinary
        assert ordinary["stage"]["id"] == "prepare"
    else:
        assert result["action"] == "run_completed", result


def test_complete_rechecks_stage_inside_run_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, selection, project, workplace = make_work(tmp_path, final_retry=True)
    final_stage(service, selection)
    other = core.process_execution_service(project, str(workplace))
    original_lock = type(service)._run_lock
    after_interleaving: list[dict[str, bytes]] = []

    @contextmanager
    def interleaved(owner: Any, run_id: str):
        if owner is not service:
            with original_lock(owner, run_id):
                yield
            return
        assert not after_interleaving
        moved = other.transition(
            **selection,
            outcome="retry",
            evidence=stage_evidence("report", "verify-ready"),
        )
        assert moved["action"] == "stage_transitioned", moved
        assert moved["stage"]["id"] == "prepare"
        after_interleaving.append(saved_work(project))
        with original_lock(owner, run_id):
            yield

    monkeypatch.setattr(type(service), "_run_lock", interleaved)
    result = service.complete(
        **selection,
        evidence=stage_evidence("brief", "prepare-ready"),
        notes="stale preflight",
    )
    assert result["action"] == "blocked", result
    assert "not_final_stage" in reason_codes(result)
    assert len(after_interleaving) == 1
    assert saved_work(project) == after_interleaving[0]


def test_complete_replays_previously_committed_nonterminal_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, selection, project, workplace = make_work(tmp_path)
    intent = project / ".pf/runs" / selection["run_id"] / "completion-intent.yaml"
    assignment = project / ".pf/assignments" / (selection["assignment_id"] + ".yaml")
    original = type(service)._atomic_text
    interrupted = False

    def stop_after_intent(owner: Any, path: Path, content: str) -> None:
        nonlocal interrupted
        if (
            owner is service
            and path == assignment
            and intent.exists()
            and not interrupted
        ):
            interrupted = True
            raise OSError("fixture committed transition interrupted")
        original(owner, path, content)

    with monkeypatch.context() as fault:
        fault.setattr(type(service), "_atomic_text", stop_after_intent)
        with pytest.raises(OSError, match="fixture committed transition interrupted"):
            service.transition(
                **selection,
                outcome="completed",
                evidence=stage_evidence("brief", "prepare-ready"),
            )
    assert interrupted and intent.exists()
    fresh = core.process_execution_service(project, str(workplace))
    recovered = fresh.complete(
        **selection, outcome="ignored-invalid-retry", notes="ignored retry note"
    )
    assert recovered["action"] == "stage_transitioned", recovered
    assert recovered["stage"]["id"] == "build"
    assert not intent.exists()
    history = yaml.safe_load(assignment.read_bytes())["stage_history"]
    assert [item["stage_id"] for item in history] == ["prepare"]
