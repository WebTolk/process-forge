#!/usr/bin/env python3
"""Probe Windows-safe temporary workspace operations without touching PF Runtime."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parents[3]


def error_payload(exc: BaseException) -> dict[str, object]:
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "winerror": getattr(exc, "winerror", None),
        "errno": getattr(exc, "errno", None),
    }


def exercise_tree(path: Path) -> dict[str, object]:
    result: dict[str, object] = {"path": str(path), "operations": {}}
    child = path / "child"
    marker = child / "marker.txt"
    renamed = child / "renamed.txt"
    try:
        child.mkdir()
        result["operations"]["child_mkdir"] = "pass"
        marker.write_text("process-forge-temp-matrix\n", encoding="utf-8")
        result["operations"]["file_write"] = "pass"
        result["operations"]["file_read"] = "pass" if marker.read_text(encoding="utf-8") else "fail"
        marker.rename(renamed)
        result["operations"]["rename"] = "pass"
        renamed.unlink()
        child.rmdir()
        result["operations"]["delete"] = "pass"
        result["status"] = "pass"
    except OSError as exc:
        result["status"] = "fail"
        result["error"] = error_payload(exc)
    return result


def create_with_temporary_directory(root: Path) -> tuple[Path, Callable[[], None]]:
    holder = tempfile.TemporaryDirectory(prefix="pf-runtime-matrix-", dir=root, ignore_cleanup_errors=True)
    return Path(holder.name), holder.cleanup


def create_with_mkdtemp(root: Path) -> tuple[Path, Callable[[], None]]:
    path = Path(tempfile.mkdtemp(prefix="pf-runtime-matrix-", dir=root))
    return path, lambda: shutil.rmtree(path, ignore_errors=True)


def create_with_os_makedirs(root: Path) -> tuple[Path, Callable[[], None]]:
    path = root / f"pf-runtime-matrix-{uuid.uuid4().hex}"
    os.makedirs(path)
    return path, lambda: shutil.rmtree(path, ignore_errors=True)


def create_with_path_mkdir(root: Path) -> tuple[Path, Callable[[], None]]:
    path = root / f"pf-runtime-matrix-{uuid.uuid4().hex}"
    path.mkdir()
    return path, lambda: shutil.rmtree(path, ignore_errors=True)


def create_with_powershell(root: Path) -> tuple[Path, Callable[[], None]]:
    path = root / f"pf-runtime-matrix-{uuid.uuid4().hex}"
    escaped_path = str(path).replace("'", "''")
    command = [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        f"New-Item -ItemType Directory -Path '{escaped_path}' -ErrorAction Stop | Out-Null",
    ]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise OSError(completed.returncode, completed.stderr.strip() or completed.stdout.strip(), str(path))
    return path, lambda: shutil.rmtree(path, ignore_errors=True)


METHODS: dict[str, Callable[[Path], tuple[Path, Callable[[], None]]]] = {
    "temporary_directory": create_with_temporary_directory,
    "mkdtemp": create_with_mkdtemp,
    "os_makedirs": create_with_os_makedirs,
    "path_mkdir": create_with_path_mkdir,
    "powershell_new_item": create_with_powershell,
}


def probe_root(label: str, root: Path) -> dict[str, object]:
    root_result: dict[str, object] = {"label": label, "root": str(root), "root_prepare": "pass", "methods": {}}
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        root_result["root_prepare"] = "fail"
        root_result["error"] = error_payload(exc)
        return root_result
    for name, creator in METHODS.items():
        try:
            path, cleanup = creator(root)
        except OSError as exc:
            root_result["methods"][name] = {"status": "fail", "error": error_payload(exc)}
            continue
        try:
            root_result["methods"][name] = exercise_tree(path)
        finally:
            cleanup()
    return root_result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    local_app_data = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    roots = {
        "system_temp": Path(tempfile.gettempdir()),
        "repo_runtime_test_temp": REPO_ROOT / ".pf" / "runtime" / "test-temp",
        "repo_dot_tmp": REPO_ROOT / ".tmp",
        "user_writable_localappdata": local_app_data / "ProcessForgeTempMatrix",
        "explicit_d_dev": Path("D:/Dev/process-forge/.pf/runtime/test-temp-explicit"),
    }
    result = {
        "schema_version": 1,
        "cwd": str(Path.cwd()),
        "temp": os.environ.get("TEMP"),
        "tmp": os.environ.get("TMP"),
        "roots": [probe_root(label, root) for label, root in roots.items()],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
