#!/usr/bin/env python3
"""Run project release gates on a fresh consumer, never on the distribution."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_step(root: Path, env: dict[str, str], *args: str) -> None:
    """Preserve the native command's output and fail before dependent steps."""
    subprocess.run(
        [sys.executable, str(ROOT / "bin/pf.py"), *args],
        cwd=root,
        env=env,
        check=True,
        timeout=60,
    )


def prepare_consumer(base: Path, env: dict[str, str]) -> Path:
    """Onboard an isolated file-only consumer and populate its event stream."""
    workplace = base / "workplace"
    project = base / "consumer"
    project.mkdir()
    run_step(
        base,
        env,
        "workplace-init",
        "--workplace",
        str(workplace),
        "--profile",
        "software-development",
        "--apply",
    )
    run_step(
        base,
        env,
        "project-onboard",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--type",
        "generic",
        "--process",
        "software-feature-development",
        "--coordination-mode",
        "simple",
        "--apply",
    )
    run_step(
        base,
        env,
        "chat-record",
        "--project-root",
        str(project),
        "--session-id",
        "release-gate",
        "--participant",
        "release-gate",
        "--participant-type",
        "agent",
        "--role",
        "assistant",
        "--content",
        "Release consumer validation",
    )
    transcripts = list((project / ".pf/runtime/chat/transcripts").glob("*.ndjson"))
    if len(transcripts) != 1 or not transcripts[0].read_bytes().strip():
        raise RuntimeError("consumer chat/event fixture was not populated")
    return project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", required=True, choices=["events-validate", "doctor-project"]
    )
    args = parser.parse_args(argv)
    # A new fixture per gate keeps --only independent of order or earlier smokes.
    with tempfile.TemporaryDirectory(prefix="pf-release-consumer-") as temporary:
        base = Path(temporary).resolve()
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("PF_", "GIT_"))
        }
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        for key in (
            "LOCALAPPDATA",
            "XDG_CONFIG_HOME",
            "XDG_DATA_HOME",
            "XDG_CACHE_HOME",
            "TEMP",
            "TMP",
            "TMPDIR",
        ):
            target = base / key.lower()
            target.mkdir()
            env[key] = str(target)
        try:
            project = prepare_consumer(base, env)
            run_step(base, env, args.check, "--project-root", str(project))
        except subprocess.CalledProcessError as error:
            print(
                f"FAIL: release consumer command exited {error.returncode}",
                file=sys.stderr,
            )
            return error.returncode if error.returncode > 0 else 1
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            print(f"FAIL: release consumer fixture: {error}", file=sys.stderr)
            return 1
    print(f"PASS: {args.check} on isolated onboarded consumer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
