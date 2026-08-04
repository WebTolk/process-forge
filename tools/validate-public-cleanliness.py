#!/usr/bin/env python3
"""Check public product files for private references and local data."""

from __future__ import annotations

import re
import sys
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIRS = ["docs", "schemas", "processes", "packages", "packs", "templates", "prompts", "examples", "policies", "seeds", "bin", "tools", "updates", "checksums"]
PUBLIC_ROOT_FILES = ["README.md", "QUICKSTART.md", "LICENSE", "NOTICE", "CHANGELOG.md", "VERSION", "requirements.txt", ".processforge-releaseignore"]
PF_PUBLIC_ROOT_FILES = [".pf/AGENTS.md", ".pf/process-forge.yaml", ".pf/hooks.yaml"]
PF_PUBLIC_DIRS: list[str] = []
PF_FLOW_DIRS = ["artifacts", "assignments", "contexts", "handoffs", "logs", "reviews"]
PF_PRIVATE_PARTS = {"runtime", "private-notes", "cache"}
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".txt", ".py", ".csv", ".sha256"}

INTERNAL_FLOW_MARKER = "." + "web" + "tolk"
FORBIDDEN_LITERAL_PATTERNS = [
    INTERNAL_FLOW_MARKER,
    "sec" + "ret=",
    "pass" + "word=",
    "scr" + "atch",
]

FORBIDDEN_REGEX_PATTERNS = [
    re.compile(r"[A-Za-z]:\\"),
    re.compile(r"/home/[A-Za-z0-9_.-]+/"),
    re.compile(r"users\\[A-Za-z0-9_.-]+", re.IGNORECASE),
]

FLOW_CORE_DIRS = {"schemas", "processes", "packages", "templates", "prompts", "bin", "tools", "updates", "policies", "seeds"}
ALLOWED_PLATFORM_ID_PREFIXES = (
    "platform.example",
    "platform.test",
    "platform.child",
    "platform.parent",
    "platform.broken",
    "platform.optional",
    "platform.missing",
    "platform.a",
    "platform.b",
    "platform.api-example-provider",
    "platform.contract",
    "platform.authoring",
    "platform.detected",
    "platform.system",
    "platform.yaml",
    "platform.yml",
)
ALLOWED_DOCS_ID_PREFIXES = (
    "docs.example",
    "docs.test",
    "docs.php",
    "docs.web",
    "docs.api",
    "docs.child",
    "docs.parent",
    "docs.required",
    "docs.optional",
    "docs.missing",
    "docs.bad",
    "docs.private",
    "docs.a",
)
PLATFORM_ID_RE = re.compile(r"(?<![A-Za-z0-9_-])(platform\.[A-Za-z0-9][A-Za-z0-9.-]*)")
DOCS_ID_RE = re.compile(r"(?<![A-Za-z0-9_-])(docs\.[A-Za-z0-9][A-Za-z0-9.-]*)")


def public_files(root_path: Path) -> list[Path]:
    files: list[Path] = []
    for name in PUBLIC_ROOT_FILES:
        path = root_path / name
        if path.is_file():
            files.append(path)
    for name in PF_PUBLIC_ROOT_FILES:
        path = root_path / name
        if path.is_file():
            files.append(path)
    for dirname in PUBLIC_DIRS:
        root = root_path / dirname
        if root.is_dir():
            files.extend(
                path
                for path in root.rglob("*")
                if path.is_file()
                and not any(part in SKIP_DIRS for part in path.relative_to(root).parts)
                and path.suffix not in SKIP_SUFFIXES
            )
    pf_root = root_path / ".pf"
    if pf_root.is_dir():
        for dirname in PF_PUBLIC_DIRS:
            root = pf_root / dirname
            if root.is_dir():
                files.extend(
                    path
                    for path in root.rglob("*")
                    if path.is_file()
                    and not any(part in SKIP_DIRS or part in PF_PRIVATE_PARTS for part in path.relative_to(pf_root).parts)
                    and path.suffix not in SKIP_SUFFIXES
                    and path.name != "process-forge.local.yaml"
                )
    return sorted(files, key=lambda path: path.relative_to(root_path).as_posix())


def flow_core_files(root_path: Path) -> list[Path]:
    files: list[Path] = []
    for dirname in FLOW_CORE_DIRS:
        root = root_path / dirname
        if not root.is_dir():
            continue
        files.extend(
            path
            for path in root.rglob("*")
            if path.is_file()
            and not any(part in SKIP_DIRS for part in path.relative_to(root).parts)
            and path.suffix.lower() in TEXT_SUFFIXES
        )
    files.extend(path for path in (root_path / name for name in PF_PUBLIC_ROOT_FILES) if path.is_file())
    return sorted(set(files), key=lambda path: path.relative_to(root_path).as_posix())


def platform_neutrality_failures(root_path: Path) -> list[str]:
    failures: list[str] = []
    for path in flow_core_files(root_path):
        rel = path.relative_to(root_path).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in PLATFORM_ID_RE.findall(text):
            normalized = match.rstrip(".,;:)]}'\"`").lower()
            if not normalized.startswith(ALLOWED_PLATFORM_ID_PREFIXES):
                failures.append(f"{rel}: non-neutral platform id {match!r}")
        for match in DOCS_ID_RE.findall(text):
            normalized = match.rstrip(".,;:)]}'\"`").lower()
            if not normalized.startswith(ALLOWED_DOCS_ID_PREFIXES):
                failures.append(f"{rel}: non-neutral docs package id {match!r}")
    return failures


def runtime_driver_neutrality_failures(root_path: Path) -> list[str]:
    failures: list[str] = []
    checked_roots = [
        root_path / "templates" / "runtime-drivers",
        root_path / "examples" / "runtime-supervisor",
        root_path / "tools" / "test_workers",
        root_path / "tools" / "test_agents",
    ]
    checked_files = [
        root_path / "templates" / "registries" / "runtime-drivers.yaml",
        root_path / "docs" / "concepts" / "runtime-drivers.md",
        root_path / "docs" / "concepts" / "process-supervisor.md",
        root_path / "docs" / "getting-started" / "runtime-driver-supervisor.md",
        root_path / "docs" / "ru" / "concepts" / "runtime-drivers.md",
        root_path / "docs" / "ru" / "concepts" / "process-supervisor.md",
        root_path / "docs" / "ru" / "getting-started" / "runtime-driver-supervisor.md",
        root_path / "processes" / "core" / "runtime-driver-registry.yaml",
        root_path / "processes" / "core" / "process-supervisor.yaml",
        root_path / "tools" / "smoke_runtime_driver_registry.py",
        root_path / "tools" / "smoke_worker_run_shell.py",
        root_path / "tools" / "smoke_process_supervisor_tick.py",
    ]
    files: list[Path] = []
    for root in checked_roots:
        if root.is_dir():
            files.extend(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES)
    files.extend(path for path in checked_files if path.is_file())
    forbidden_terms = [
        "cod" + "ex",
        "cla" + "ude",
        "open" + "ai",
        "chat" + "gpt",
        "anth" + "ropic",
    ]
    provider_specific_driver_files = {
        "templates/registries/runtime-drivers.yaml",
        "templates/runtime-drivers/codex-exec.yaml",
        "docs/concepts/runtime-drivers.md",
        "tools/smoke_runtime_driver_registry.py",
    }
    for path in sorted(set(files), key=lambda item: item.relative_to(root_path).as_posix()):
        rel = path.relative_to(root_path).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for term in forbidden_terms:
            if term == "codex" and rel in provider_specific_driver_files:
                continue
            if term in text:
                failures.append(f"{rel}: runtime driver surface mentions agent ecosystem term {term!r}")
    return failures


RUSSIAN_MOJIBAKE_MARKERS = ("Рџ", "РЎ", "РЋ", "Р€", "вЂ", "Гђ", "Г‘")


def russian_docs_mojibake_failures(root_path: Path) -> list[str]:
    failures: list[str] = []
    files = [root_path / "README.ru.md", root_path / "QUICKSTART.ru.md"]
    ru_root = root_path / "docs" / "ru"
    if ru_root.is_dir():
        files.extend(path for path in ru_root.rglob("*.md") if path.is_file())
    for path in sorted({path for path in files if path.is_file()}, key=lambda item: item.relative_to(root_path).as_posix()):
        text = path.read_text(encoding="utf-8", errors="replace")
        markers = [marker for marker in RUSSIAN_MOJIBAKE_MARKERS if marker in text]
        if markers:
            failures.append(f"{path.relative_to(root_path).as_posix()}: mojibake markers {', '.join(markers)}")
    return failures


def validate_releaseignore(root_path: Path) -> list[str]:
    failures: list[str] = []
    path = root_path / ".processforge-releaseignore"
    if not path.is_file():
        failures.append(".processforge-releaseignore missing")
        return failures
    lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip() and not line.strip().startswith("#")]
    required = [
        ".idea/",
        ".serena/",
        ".pf/process-forge.local.yaml",
        ".pf/runtime/",
        ".pf/artifacts/",
        ".pf/reviews/",
        ".pf/handoffs/",
        ".pf/runs/",
        ".pf/contexts/",
        ".pf/assignments/",
        ".pf/dogfooding/",
        ".pf/private-notes/",
        ".pf/cache/",
        "/задания",
        "tools/__pycache__/",
        "*.pyc",
    ]
    for item in required:
        if item not in lines:
            failures.append(f".processforge-releaseignore missing {item}")
    broad_forbidden = {"artifacts/", "assignments/", "logs/", "reviews/", "handoffs/", "contexts/"}
    for item in broad_forbidden:
        if item in lines:
            failures.append(f".processforge-releaseignore excludes whole skeleton directory {item}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT), help="ProcessForge root path.")
    args = parser.parse_args()
    root_path = Path(args.root).expanduser().resolve()
    failures: list[str] = []
    for path in public_files(root_path):
        rel = path.relative_to(root_path).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        lower = text.lower()
        for marker in FORBIDDEN_LITERAL_PATTERNS:
            if marker in lower:
                failures.append(f"{rel}: forbidden marker {marker!r}")
        for pattern in FORBIDDEN_REGEX_PATTERNS:
            if pattern.search(text):
                failures.append(f"{rel}: forbidden private/local path pattern {pattern.pattern!r}")
    failures.extend(platform_neutrality_failures(root_path))
    failures.extend(runtime_driver_neutrality_failures(root_path))
    failures.extend(russian_docs_mojibake_failures(root_path))
    failures.extend(validate_releaseignore(root_path))
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: public cleanliness checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
