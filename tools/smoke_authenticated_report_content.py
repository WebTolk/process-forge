#!/usr/bin/env python3
"""Keep diagnostic path text only for authenticated, secret-free PF reports."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import tempfile
from pathlib import Path

import processforge as core
from pf_runtime import host
from smoke_conversation_completeness import setup_worker_project, transcript, worker_envelope


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-report-content-") as raw:
        _, project, _, run_id, task_id, attempt, report_rel = setup_worker_project(Path(raw))
        content = "# Report\nSource: " + str((project / "src/module.py").resolve()) + "\n"
        (project / report_rel).write_text(content, encoding="utf-8")
        session = f"pf-worker:{run_id}:{task_id}:attempt:{attempt}"

        def envelope(text=content):
            digest = "sha256:" + hashlib.sha256(text.encode()).hexdigest()
            return worker_envelope(project, run_id, task_id, attempt, report_rel, "WorkerExpectedReportCaptured", text,
                                   native_event_id=f"worker-output:{run_id}:{task_id}:attempt:{attempt}:{digest}")

        mutations = [
            lambda e: e.update(native_event_id="forged"),
            lambda e: e["raw_payload"].update(attempt="999"),
            lambda e: e["raw_payload"].update(report_hash="sha256:forged"),
            lambda e: e["raw_payload"].update(expected_report="../outside.md"),
            lambda e: e["derived_conversation_messages"][0].update(session_id="foreign"),
            lambda e: e["derived_conversation_messages"][0]["content_source"].update(content_provenance="provider_payload"),
        ]
        for index, mutate in enumerate(mutations):
            candidate = content + f"Case {index}\n"
            (project / report_rel).write_text(candidate, encoding="utf-8")
            forged = envelope(candidate)
            mutate(forged)
            result = host.ingest_event(forged, None, core)
            assert not result.get("chat_message_ids"), result
        # Authentication must not exempt credentials from the existing scanner.
        secret = "api_key=" + "private-fixture-value-123456789"
        assert core.contains_secret_value(secret)
        (project / report_rel).write_text(secret, encoding="utf-8")
        result = host.ingest_event(envelope(secret), None, core)
        assert not result.get("chat_message_ids"), result
        (project / report_rel).write_text(content, encoding="utf-8")
        for _ in range(2):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = core.command_worker_run_collect(argparse.Namespace(project_root=str(project), task=task_id))
            assert result == 0, output.getvalue()
        rows = transcript(project, session)
        assert len(rows) == 1 and rows[0]["message"]["content"] == content, rows
        assert not host._is_safe_automatic_content(content), "native host path filtering changed"
    print("PASS: authenticated path report collected exactly once; forged provenance/hash and secrets denied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
