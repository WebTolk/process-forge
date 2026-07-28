#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import io
import tempfile
from pathlib import Path

from core_boundary_smoke_helpers import write_pf_distribution, write_project
from processforge import command_doctor_project


def doctor_output(project: Path) -> tuple[int, str]:
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        status = command_doctor_project(argparse.Namespace(project_root=str(project)))
    return status, stream.getvalue()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-core-type-") as raw:
        generic = write_pf_distribution(Path(raw) / "generic")
        write_project(generic, project_type="software-project")
        (generic / ".gitignore").write_text(".pf/process-forge.local.yaml\n.pf/runtime/\n.pf/cache/\n", encoding="utf-8")
        status, output = doctor_output(generic)
        assert status != 0, output
        assert "project root looks like ProcessForge distribution" in output, output

        explicit = write_pf_distribution(Path(raw) / "explicit")
        write_project(explicit, project_type="processforge-development")
        (explicit / ".gitignore").write_text(".pf/process-forge.local.yaml\n.pf/runtime/\n.pf/cache/\n", encoding="utf-8")
        _status, output = doctor_output(explicit)
        assert "ProcessForge distribution root allowed by explicit project type" in output, output
        assert "project root looks like ProcessForge distribution" not in output, output
    print("PASS: ProcessForge core project requires explicit type")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
