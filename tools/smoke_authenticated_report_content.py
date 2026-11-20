#!/usr/bin/env python3
"""Keep diagnostic path text only for authenticated, secret-free PF reports."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Any, Callable

from pf_runtime import host
from smoke_conversation_completeness import (
    assert_denied,
    event,
    pf,
    setup_worker_project,
    transcript,
    worker_envelope,
)

from processforge_core.common.privacy import contains_secret_value


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-report-content-") as raw:
        root = Path(raw)
        workplace, project, _, run_id, task_id, attempt, report_rel = (
            setup_worker_project(root)
        )
        content = (
            "# Report\nSource: " + str((project / "src/module.py").resolve()) + "\n"
        )
        (project / report_rel).write_text(content, encoding="utf-8")
        session = f"pf-worker:{run_id}:{task_id}:attempt:{attempt}"

        def envelope(text: str = content) -> dict[str, Any]:
            digest = "sha256:" + hashlib.sha256(text.encode()).hexdigest()
            return worker_envelope(
                project,
                run_id,
                task_id,
                attempt,
                report_rel,
                "WorkerExpectedReportCaptured",
                text,
                native_event_id=f"worker-output:{run_id}:{task_id}:attempt:{attempt}:{digest}",
            )

        mutations: list[Callable[[dict[str, Any]], None]] = [
            lambda e: e.update(native_event_id="forged"),
            lambda e: e["raw_payload"].update(attempt="999"),
            lambda e: e["raw_payload"].update(report_hash="sha256:forged"),
            lambda e: e["raw_payload"].update(expected_report="../outside.md"),
            lambda e: e["derived_conversation_messages"][0].update(
                session_id="foreign"
            ),
            lambda e: e["derived_conversation_messages"][0]["content_source"].update(
                content_provenance="provider_payload"
            ),
            lambda e: e["derived_conversation_messages"][0]["participant"].update(
                id="forged-owner"
            ),
            lambda e: e["derived_conversation_messages"][0].update(
                turn_id="forged-turn"
            ),
            lambda e: e["derived_conversation_messages"][0]["delivery"].update(
                sequence=999
            ),
        ]
        for index, mutate in enumerate(mutations):
            candidate = content + f"Case {index}\n"
            (project / report_rel).write_text(candidate, encoding="utf-8")
            forged = envelope(candidate)
            mutate(forged)
            result = event(workplace, forged, root / f"forged-{index}.json")
            assert result.get("accepted") and result.get("chat_message_ids") == [], (
                result
            )
            diagnostics = result["diagnostics"]
            assert isinstance(diagnostics, dict), result
            denial = diagnostics["conversation"]
            assert denial["status"] == "denied" and denial["reason"] in {
                "provenance_rejected",
                "session_not_authorized",
            }, result
            assert transcript(project, session) == [], result
        # Authentication must not exempt credentials from the existing scanner.
        secret = "api_key=" + "private-fixture-value-123456789"
        assert contains_secret_value(secret)
        (project / report_rel).write_text(secret, encoding="utf-8")
        result = event(workplace, envelope(secret), root / "secret.json")
        assert_denied(result, "unsafe_automatic_content")
        assert transcript(project, session) == [], result
        (project / report_rel).write_text(content, encoding="utf-8")
        for expected_output in (
            f"DONE: {task_id}",
            f"COLLECTED: {task_id} already collected for attempt {attempt}",
        ):
            output = pf(
                "worker-run",
                "collect",
                "--project-root",
                str(project),
                "--task",
                task_id,
            )
            assert expected_output in output, output
        rows = transcript(project, session)
        assert len(rows) == 1, rows
        message = rows[0]["message"]
        assert isinstance(message, dict), rows
        assert message["content"] == content, rows
        assert not host._is_safe_automatic_content(content), (
            "native host path filtering changed"
        )
    print(
        "PASS: authenticated path report collected exactly once; forged provenance/hash and secrets denied"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
