#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import io
import sys
import tempfile
import zipfile
from pathlib import Path

import processforge


def run_case(scale: object, expected_arg: str, expected_timeout: int) -> None:
    calls: list[tuple[str, list[str], int]] = []

    def fake_run(label: str, command: list[str], cwd: Path, timeout: int, **kwargs: object) -> processforge.ReleaseCommandResult:
        calls.append((label, command, timeout))
        return processforge.ReleaseCommandResult(
            label,
            "PASS",
            0,
            "",
            processforge.now_utc(),
            processforge.now_utc(),
            0.0,
            timeout,
            command,
        )

    with tempfile.TemporaryDirectory(prefix="pf-archive-scale-") as raw:
        root = Path(raw)
        archive_path = root / "processforge.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("tools/processforge.py", "# extracted cli fixture\n")
            archive.writestr("bin/pf.py", "# extracted launcher fixture\n")

        original_inspect = processforge.inspect_release_archive
        original_run = processforge.run_release_command
        try:
            processforge.inspect_release_archive = lambda archive, manifest=None: [processforge.check("PASS", "fixture archive")]
            processforge.run_release_command = fake_run
            rc = processforge.command_release_archive_test(
                argparse.Namespace(
                    archive=str(archive_path),
                    manifest=None,
                    root=None,
                    extracted_test="quick",
                    timeout_scale=scale,
                )
            )
        finally:
            processforge.inspect_release_archive = original_inspect
            processforge.run_release_command = original_run

    assert rc == 0
    nested = [item for item in calls if item[0] == "release-test extracted archive"]
    assert len(nested) == 1, calls
    _, command, timeout = nested[0]
    assert "--timeout-scale" in command, command
    index = command.index("--timeout-scale")
    assert command[index + 1] == expected_arg, command
    assert timeout == expected_timeout, timeout


def rejected(scale: object) -> None:
    with tempfile.TemporaryDirectory(prefix="pf-archive-scale-reject-") as raw:
        root = Path(raw)
        archive_path = root / "processforge.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("tools/processforge.py", "# extracted cli fixture\n")
        original_inspect = processforge.inspect_release_archive
        try:
            processforge.inspect_release_archive = lambda archive, manifest=None: [processforge.check("PASS", "fixture archive")]
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                rc = processforge.command_release_archive_test(
                    argparse.Namespace(
                        archive=str(archive_path),
                        manifest=None,
                        root=None,
                        extracted_test="quick",
                        timeout_scale=scale,
                    )
                )
        finally:
            processforge.inspect_release_archive = original_inspect

    assert rc == 1
    assert "--timeout-scale must be a finite value greater than 0" in output.getvalue()


def main() -> int:
    run_case(None, "1.0", 1200)
    run_case(2, "2.0", 2400)
    rejected(0)
    rejected(-1)
    rejected(float("nan"))
    rejected(float("inf"))
    print("PASS: release-archive-test propagates finite timeout-scale to extracted release-test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
