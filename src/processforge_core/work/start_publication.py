"""Publish an already permitted Work start through existing ordered operations."""
from __future__ import annotations

import hashlib
import json
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from .capsule_publication import publish_capsule_bytes
from .start_intent import (
    RENDERING_START,
    StartIntentError,
    applied_path,
    fingerprint,
    intent_path,
    read_record,
    validate,
)


class StartEventWriter(Protocol):
    def __call__(
        self,
        event_type: str,
        run: dict[str, Any],
        assignment: dict[str, Any],
        stage_id: str,
        *,
        outcome: str,
        previous_stage_id: str = "",
        next_stage_id: str = "",
        event_id: str | None = None,
    ) -> None: ...


class StartStateReader(Protocol):
    def __call__(self, *, run_id: str, assignment_id: str, session_id: str) -> dict[str, Any]: ...


@dataclass(frozen=True, kw_only=True)
class WorkStartPublicationService:
    run_path: Callable[[], Callable[[str], Path]] = field(repr=False, compare=False)
    assignment_path: Callable[[], Callable[[str], Path]] = field(repr=False, compare=False)
    atomic_yaml: Callable[[], Callable[[Path, dict[str, Any]], Any]] = field(repr=False, compare=False)
    atomic_text: Callable[[], Callable[[Path, str], Any]] = field(repr=False, compare=False)
    write_task_index: Callable[[], Callable[[dict[str, Any]], Any]] = field(repr=False, compare=False)
    emit: Callable[[], StartEventWriter] = field(repr=False, compare=False)
    state: Callable[[], StartStateReader] = field(repr=False, compare=False)
    write_projection: Callable[[], Callable[[dict[str, Any]], Any]] = field(repr=False, compare=False)

    def publish(
        self,
        *,
        run_id: str,
        assignment_id: str,
        run: dict[str, Any],
        assignment: dict[str, Any],
        stage_id: str,
        objective: str,
        stages: list[dict[str, Any]],
        stage_override: str,
        session_id: str,
        project_id: str,
        capsule_text: str,
        request: dict[str, Any],
        admission: Callable[[], AbstractContextManager[Any]] = nullcontext,
    ) -> dict[str, Any]:
        intent = {
            "schema_version": 1,
            "kind": "pf.work.start-intent",
            "project_id": project_id,
            "run": run,
            "assignment": assignment,
            "stage_id": stage_id,
            "objective": objective,
            "stages": [str(item.get("id")) for item in stages],
            "stage_override": stage_override,
            "capsule_text": capsule_text,
            "request": request,
        }
        intent["checksum"] = fingerprint(intent)
        return self.replay(intent, session_id=session_id, admission=admission)

    def replay(
        self,
        intent: dict[str, Any],
        *,
        session_id: str,
        admission: Callable[[], AbstractContextManager[Any]] = nullcontext,
    ) -> dict[str, Any]:
        run, assignment = intent["run"], intent["assignment"]
        run_id, assignment_id = str(run["id"]), str(assignment["id"])
        stage_id, objective = str(intent["stage_id"]), str(intent["objective"])
        run_path = self.run_path()(run_id)
        assignment_path = self.assignment_path()(assignment_id)
        validate(intent, run_path, str(intent["project_id"]))
        journal = intent_path(run_path)
        phase = "admission"
        try:
            # Keep this scope short: exact authoritative files and the four SQL
            # admissions only. Mandatory dispatch closes the context; state and
            # projections run after the admission/native/identity gates release.
            with admission():
                phase = "intent"
                if journal.exists():
                    if read_record(journal) != intent:
                        raise StartIntentError()
                else:
                    self.atomic_text()(
                        journal,
                        json.dumps(intent, ensure_ascii=False, sort_keys=True) + "\n",
                    )
                phase = "documents"
                capsule = (
                    run_path.parent.parent.parent
                    / "contexts"
                    / "assignment-capsules"
                    / f"{assignment_id}.capsule.yaml"
                )
                raw = intent["capsule_text"].encode("utf-8")
                if capsule.exists():
                    if capsule.is_symlink() or capsule.read_bytes() != raw:
                        raise StartIntentError("work_start_concurrent_change")
                else:
                    publish_capsule_bytes(capsule, raw)
                import yaml

                for path, document in ((run_path, run), (assignment_path, assignment)):
                    if path.exists():
                        if (
                            path.is_symlink()
                            or yaml.safe_load(path.read_text(encoding="utf-8"))
                            != document
                        ):
                            raise StartIntentError("work_start_concurrent_change")
                    else:
                        self.atomic_yaml()(path, document)
                self.atomic_text()(
                    run_path.parent / "plan.md",
                    f"# Run Plan: {objective[:80]}\n\nObjective: {objective}\n",
                )
                self.write_task_index()(run)
                phase = "events"
                for event_type in (
                    "run.created",
                    "task.created",
                    "assignment.created",
                    "process.stage.started",
                ):
                    event_id = (
                        "evt_"
                        + hashlib.sha256(
                            (intent["checksum"] + event_type).encode()
                        ).hexdigest()[:32]
                    )
                    self.emit()(
                        event_type,
                        run,
                        assignment,
                        stage_id,
                        outcome="started",
                        previous_stage_id="",
                        next_stage_id=stage_id
                        if event_type == "process.stage.started"
                        else "",
                        event_id=event_id,
                    )
                phase = "event_commit_and_dispatch"
            phase = "projection"
            token = RENDERING_START.set((str(run_path), intent["checksum"]))
            try:
                state = self.state()(
                    run_id=run_id, assignment_id=assignment_id, session_id=session_id
                )
            finally:
                RENDERING_START.reset(token)
            self.write_projection()(state)
            phase = "receipt"
            self.atomic_text()(
                applied_path(run_path),
                json.dumps(
                    {
                        "schema_version": 1,
                        "checksum": intent["checksum"],
                        "status": "applied",
                    },
                    sort_keys=True,
                )
                + "\n",
            )
        except BaseException as error:
            # The original mandatory failure still escapes. This private receipt
            # makes a committed/partially committed start distinguishable from
            # admission refusal, even when MCP exposes only the original code.
            if journal.exists():
                try:
                    self.atomic_text()(
                        run_path.parent / "start-failure.json",
                        json.dumps(
                            {
                                "schema_version": 1,
                                "checksum": intent["checksum"],
                                "run_id": run_id,
                                "assignment_id": assignment_id,
                                "phase": phase,
                                "code": getattr(error, "code", type(error).__name__),
                            },
                            sort_keys=True,
                        )
                        + "\n",
                    )
                except (OSError, ValueError):
                    pass  # A diagnostic write must never replace the cause.
            raise
        return {
            "schema_version": 1,
            "kind": "pf.work.start",
            "action": "created_new",
            "project": state.get("project", {}),
            "run_id": run_id,
            "assignment_id": assignment_id,
            "stage": stage_id,
            "valid_stages": intent["stages"],
            "stage_selection": "preferred"
            if intent["stage_override"]
            else "process_initial_stage",
            "session": {"status": "bound", "id": session_id}
            if session_id
            else {"status": "absent"},
            "obligations": state.get("obligations", []),
            "gates": state.get("gates", {}),
            "work_state": state,
            "context": state.get("context", {}),
        }
