"""Install shared development tools outside projects and the replaceable PF Core."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil

# Only explicitly selected interpreters and managed package commands are run.
import subprocess  # nosec B404
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True)  # nosec B603


def install(
    source: Path, destination: Path, python: str, toolchains: Path | None = None
) -> dict:
    """Deploy a managed bundle and install its pinned development dependencies.

    Args:
        source: Reviewed portable bundle directory.
        destination: Shared tool directory outside project repositories and PF Core.
        python: Base interpreter executable, Python 3.11 or newer.
        toolchains: Optional shared toolchain contract directory.

    Returns:
        The completed private installation receipt.

    Raises:
        ValueError: The bundle is invalid or the interpreter version is unsupported.
        OSError: Deployment or backup fails.
        subprocess.CalledProcessError: Environment creation or installation fails.
    """
    source, destination = source.resolve(), destination.expanduser().resolve()
    info_script = "import json,sys;print(json.dumps({'version':list(sys.version_info[:2]),'executable':sys.executable}))"
    result = subprocess.run(
        [python, "-I", "-c", info_script], capture_output=True, text=True, check=True
    )  # nosec B603
    base = json.loads(result.stdout)
    if tuple(base["version"]) < (3, 11):
        raise ValueError("Shared Python QA requires Python 3.11 or newer")
    files = [
        "qa.py",
        "install.py",
        "requirements.txt",
        "README.md",
        "toolchain.json",
        "config/ruff.toml",
        "config/mypy.ini",
        "config/bandit.yaml",
    ]
    if (source / "requirements.lock.txt").is_file():
        files.append("requirements.lock.txt")
    for name in files:
        if not (source / name).is_file():
            raise ValueError("Incomplete shared QA bundle: " + name)
    destination.mkdir(parents=True, exist_ok=True)
    previous = destination / "installed.json"
    if previous.is_file():
        installed = json.loads(previous.read_text(encoding="utf-8"))
        if installed.get("python_version") != base["version"]:
            raise ValueError(
                "Use another shared tool directory for a different Python major/minor version"
            )
    executable = (
        destination
        / ".venv"
        / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    )
    if not executable.is_file():
        _run([base["executable"], "-m", "venv", str(destination / ".venv")])
    current = subprocess.run(
        [str(executable), "-I", "-c", info_script],
        capture_output=True,
        text=True,
        check=True,
    )  # nosec B603
    if json.loads(current.stdout)["version"] != base["version"]:
        raise ValueError(
            "Existing shared environment uses another Python major/minor version"
        )
    backup = (
        destination
        / "backups"
        / (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + "-"
            + uuid4().hex[:8]
        )
    )
    for name in files:
        src, dst = source / name, destination / name
        if src == dst or (dst.is_file() and src.read_bytes() == dst.read_bytes()):
            continue
        if dst.exists():
            saved = backup / name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, saved)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    requirement = destination / (
        "requirements.lock.txt"
        if (destination / "requirements.lock.txt").is_file()
        else "requirements.txt"
    )
    _run(
        [
            str(executable),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "-r",
            str(requirement),
        ]
    )
    _run([str(executable), "-m", "pip", "check"])
    receipt = {
        "schema_version": 1,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "base_python": base["executable"],
        "python_version": base["version"],
        "files": {
            name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
            for name in files
        },
    }
    if toolchains is not None:
        contract = toolchains.expanduser().resolve() / "python" / "toolchain.json"
        contract.parent.mkdir(parents=True, exist_ok=True)
        if (
            contract.is_file()
            and contract.read_bytes() != (source / "toolchain.json").read_bytes()
        ):
            backup.mkdir(parents=True, exist_ok=True)
            shutil.copy2(contract, backup / "previous-toolchain.json")
        shutil.copy2(source / "toolchain.json", contract)
        receipt["toolchain_contract"] = str(contract)
    temporary = previous.with_name(".installed." + uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        temporary.replace(previous)
    finally:
        temporary.unlink(missing_ok=True)
    return receipt


def main(argv: list[str] | None = None) -> int:
    """Install only at the operator's explicitly selected shared destination."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tools-root",
        type=Path,
        required=True,
        help="Shared python-qa directory, outside projects and PF Core",
    )
    parser.add_argument("--toolchains-root", type=Path)
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args(argv)
    try:
        receipt = install(
            Path(__file__).resolve().parent,
            args.tools_root,
            args.python,
            args.toolchains_root,
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print("Python QA installation failed: " + str(exc), file=sys.stderr)
        return 1
    print(
        "Installed shared Python QA for Python "
        + ".".join(map(str, receipt["python_version"]))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
