#!/usr/bin/env python3
"""Reject report escapes before real worker collection or host file reads."""
from __future__ import annotations

import argparse
import contextlib
import io
import tempfile
from pathlib import Path
from unittest.mock import patch

import processforge as core
from pf_runtime import host
from smoke_conversation_completeness import setup_worker_project, transcript, worker_envelope


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-report-containment-") as raw:
        root = Path(raw)
        _, project, _, run_id, task_id, attempt, valid_report = setup_worker_project(root)
        outside = root / "outside.md"
        marker = "ExternalReportMustNeverBeRead"
        outside.write_text(marker, encoding="utf-8")
        paths = ["../outside.md", "..\\outside.md", str(outside), "Q:" + "outside.md", "/outside.md"]
        link = project / "linked-report.md"
        try:
            link.symlink_to(outside)
            paths.append(link.name)
        except (OSError, NotImplementedError):
            print("SKIP: symlink creation unavailable")
        read_text = Path.read_text
        read_bytes = Path.read_bytes

        def guarded_read(path, *args, **kwargs):
            assert path.resolve() != outside.resolve(), "external report read attempted"
            return read_text(path, *args, **kwargs)

        def guarded_bytes(path):
            assert path.resolve() != outside.resolve(), "external report byte read attempted"
            return read_bytes(path)

        for report_rel in paths:
            task = core.load_task(project, task_id)
            task["expected_report"]["artifact"] = report_rel
            task["required_outputs"][0]["path"] = report_rel
            core.save_task(project, task)
            with patch.object(Path, "read_text", guarded_read), patch.object(Path, "read_bytes", guarded_bytes):
                assert core.task_output_path(project, {"path": report_rel}) is None
                assert any(item.level == "FAIL" for item in core.required_output_checks(project, task))
                assert core.task_verification_fingerprint(project, task).startswith("sha256:")
                with contextlib.redirect_stdout(io.StringIO()):
                    assert core.command_task_doctor(argparse.Namespace(project_root=str(project), task=task_id)) == 1
                    assert core.command_worker_run_collect(argparse.Namespace(project_root=str(project), task=task_id)) == 1
                envelope = worker_envelope(project, run_id, task_id, attempt, report_rel, "WorkerExpectedReportCaptured", marker)
                assert host._worker_session_authorized(envelope, project, core) is False
            assert not transcript(project, f"pf-worker:{run_id}:{task_id}:attempt:{attempt}")
            for path in (project / ".pf/runtime").rglob("*"):
                if path.is_file() and path.suffix in {".json", ".ndjson", ".md"}:
                    assert marker not in path.read_text(encoding="utf-8", errors="replace"), path
        task["expected_report"]["artifact"] = valid_report
        task["required_outputs"][0]["path"] = valid_report
        core.save_task(project, task)
        (project / valid_report).write_text("# Authorized report\n", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            assert core.command_worker_run_collect(argparse.Namespace(project_root=str(project), task=task_id)) == 0
        assert len(transcript(project, f"pf-worker:{run_id}:{task_id}:attempt:{attempt}")) == 1
    print("PASS: report traversal, absolute and symlink escapes rejected before reads; valid collection works")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
