"""Exercise global agent navigation through the native ProcessForge launcher."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

CLI = Path(__file__).resolve().parents[2] / "bin/pf.py"
START = b"<!-- PROCESSFORGE:START -->"
END = b"<!-- PROCESSFORGE:END -->"
TRIGGER = '- the user says "по флоу";'
MAX_SECTION_BYTES = 4096


def _run_pf(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Keep subprocess configuration and temporary files within the test root."""
    env = os.environ.copy()
    env.update(
        dict.fromkeys(
            (
                "HOME",
                "USERPROFILE",
                "APPDATA",
                "LOCALAPPDATA",
                "XDG_CONFIG_HOME",
                "XDG_DATA_HOME",
                "XDG_CACHE_HOME",
                "TEMP",
                "TMP",
                "TMPDIR",
            ),
            str(root),
        )
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )


def _assert_status(
    result: subprocess.CompletedProcess[str], status: str, target: Path
) -> None:
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert result.stdout == f"{status}: {target.resolve()}\n"


def _assert_global_section(section: bytes) -> None:
    lines = section.decode("utf-8", errors="strict").splitlines()
    assert lines[0] == START.decode("ascii")
    assert lines[-1] == END.decode("ascii")
    assert section.count(START) == section.count(END) == 1
    if lines.count(TRIGGER) != 1:
        pytest.fail(
            f"Expected exactly one canonical trigger line {TRIGGER!r}", pytrace=False
        )
    assert len(section) <= MAX_SECTION_BYTES
    root_entry = (
        "2. Read the project's root `AGENTS.md`. If an unmigrated project has no"
    )
    assert root_entry in lines
    assert lines[lines.index(root_entry) + 1] == "   root entry, read `.pf/AGENTS.md`."
    for pointer in ("`.pf/process-forge.yaml`", "`pf.context`"):
        assert any(pointer in line for line in lines), pointer


def test_global_agents_section_creates_compact_utf8_and_repeats(tmp_path: Path) -> None:
    target = tmp_path / "global" / "AGENTS.md"
    arguments = ("global-agents-section", "--path", str(target))

    _assert_status(_run_pf(tmp_path, *arguments), "WRITTEN", target)
    original = target.read_bytes()
    _assert_status(_run_pf(tmp_path, *arguments), "UNCHANGED", target)
    assert target.read_bytes() == original
    assert not target.with_suffix(".md.candidate").exists()
    _assert_global_section(original)


@pytest.mark.parametrize(
    "preview_flags", [(), ("--dry-run", "--force")], ids=["default", "explicit"]
)
def test_global_agents_section_previews_and_replaces_only_owned_block(
    tmp_path: Path, preview_flags: tuple[str, ...]
) -> None:
    target = tmp_path / "Мои заметки 数据" / "AGENTS.md"
    target.parent.mkdir()
    candidate = target.with_suffix(".md.candidate")
    newline = os.linesep.encode("ascii")
    prefix = "# Правила команды 数据".encode("utf-8") + newline * 2
    suffix = newline * 2 + "Сохранить этот абзац 日本語.".encode("utf-8") + newline
    damaged = b"- " + "РїРѕ С„Р»РѕСѓ".encode("utf-8")
    original = prefix + newline.join((START, damaged, END)) + suffix
    target.write_bytes(original)
    arguments = ("global-agents-section", "--path", str(target))

    _assert_status(
        _run_pf(tmp_path, *arguments, *preview_flags), "CANDIDATE", candidate
    )
    assert target.read_bytes() == original
    preview = candidate.read_bytes()

    _assert_status(_run_pf(tmp_path, *arguments, "--force"), "WRITTEN", target)
    assert target.read_bytes() == preview
    assert preview.startswith(prefix)
    assert preview.endswith(suffix)
    _assert_global_section(preview[len(prefix) : -len(suffix)])


def test_init_workplace_writes_the_same_global_agents_section(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    _assert_status(
        _run_pf(tmp_path, "global-agents-section", "--path", str(target)),
        "WRITTEN",
        target,
    )

    workplace = tmp_path / "workplace"
    result = _run_pf(tmp_path, "init-workplace", "--root", str(workplace), "--apply")
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert "WRITTEN: AGENTS.md" in result.stdout.splitlines()
    section = (workplace / "AGENTS.md").read_bytes()
    assert section == target.read_bytes()
    _assert_global_section(section)


def test_global_agents_section_refuses_a_regular_file_parent(tmp_path: Path) -> None:
    obstruction = tmp_path / "regular-file"
    original = b"Preserve this regular file.\n"
    obstruction.write_bytes(original)
    result = _run_pf(
        tmp_path,
        "global-agents-section",
        "--path",
        str(obstruction / "AGENTS.md"),
        "--force",
    )

    assert result.returncode == 1, result.stderr
    assert result.stdout == ""
    assert result.stderr, "Expected the filesystem failure on stderr"
    diagnostic = result.stderr.splitlines()[-1]
    assert diagnostic.startswith("FileExistsError:")
    assert obstruction.name in diagnostic
    assert list(tmp_path.iterdir()) == [obstruction]
    assert obstruction.read_bytes() == original
