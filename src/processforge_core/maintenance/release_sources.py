"""Release source filtering policy: existing algorithms owned by Core."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from processforge_core.common.paths import rel

RELEASE_DIRS = ["docs", "schemas", "processes", "packages", "packs", "templates", "prompts", "examples", "policies", "seeds", "bin", "src", "tools", "updates", "checksums"]

RELEASE_ROOT_FILES = ["README.md", "README.ru.md", "QUICKSTART.md", "QUICKSTART.ru.md", "CHANGELOG.md", "LICENSE", "NOTICE", "VERSION", "requirements.txt", ".gitignore", ".processforge-releaseignore"]

RELEASE_PF_PUBLIC_FILES = [".pf/AGENTS.md", ".pf/process-forge.yaml", ".pf/hooks.yaml"]

RELEASE_FORBIDDEN_DIR_PARTS = {
    ".git",
    ".idea",
    ".serena",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "private-notes",
}

RELEASE_FORBIDDEN_PF_PREFIXES = (
    ".pf/runtime/",
    ".pf/artifacts/",
    ".pf/reviews/",
    ".pf/handoffs/",
    ".pf/runs/",
    ".pf/contexts/",
    ".pf/assignments/",
    ".pf/dogfooding/",
)

RELEASE_FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".ps1", ".zip"}

RELEASE_ALLOWED_PROJECTION_DIRTY_PATHS = {
    ".pf/artifacts/projections/command-history.md",
    ".pf/artifacts/projections/stage-obligations.json",
}


class ReleaseSourcePolicy:
    def release_ignore_patterns(self, root: Path) -> list[str]:
        path = root / ".processforge-releaseignore"
        if not path.is_file():
            return []
        patterns: list[str] = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            value = line.strip()
            if value and not value.startswith("#"):
                patterns.append(value.replace("\\", "/"))
        return patterns

    def release_ignore_match(self, rel_path: str, patterns: list[str]) -> bool:
        normalized = rel_path.replace("\\", "/").lstrip("./")
        for pattern in patterns:
            candidate = pattern.lstrip("./")
            if candidate.startswith("/"):
                candidate = candidate[1:]
            if candidate.endswith("/"):
                prefix = candidate.rstrip("/")
                if normalized == prefix or normalized.startswith(prefix + "/"):
                    return True
            if fnmatch.fnmatch(normalized, candidate) or fnmatch.fnmatch(Path(normalized).name, candidate):
                return True
            if normalized == candidate:
                return True
        return False

    def release_source_files(self, root: Path) -> list[tuple[str, Path]]:
        files: list[tuple[str, Path]] = []
        for name in RELEASE_ROOT_FILES:
            path = root / name
            if path.is_file():
                files.append((name, path))
        root_agents = root / "AGENTS.md"
        if root_agents.is_file():
            files.append(("AGENTS.md", root_agents))
        for name in RELEASE_PF_PUBLIC_FILES:
            path = root / name
            if path.is_file():
                files.append((name, path))
        for dirname in RELEASE_DIRS:
            base = root / dirname
            if base.is_dir():
                for path in base.rglob("*"):
                    if path.is_file():
                        files.append((rel(path, root), path))
        return sorted(files, key=lambda item: item[0])

    def release_path_is_forbidden(self, rel_path: str) -> str | None:
        normalized = rel_path.replace("\\", "/")
        if normalized.startswith(("processes/user/", "processes/custom/")) and Path(normalized).name != ".gitkeep":
            return "private user/custom process definition"
        for prefix in RELEASE_FORBIDDEN_PF_PREFIXES:
            if normalized == prefix.rstrip("/") or normalized.startswith(prefix):
                return f"forbidden .pf release prefix {prefix.rstrip('/')}"
        parts = Path(rel_path).parts
        suffix = Path(rel_path).suffix.lower()
        for part in parts:
            if part in RELEASE_FORBIDDEN_DIR_PARTS:
                return f"forbidden directory part {part}"
        if suffix in RELEASE_FORBIDDEN_SUFFIXES:
            return f"forbidden suffix {suffix}"
        if rel_path.endswith(".env") or "/.env" in rel_path or Path(rel_path).name.startswith(".env."):
            return "private env file"
        if Path(rel_path).name == "process-forge.local.yaml" and not rel_path.startswith(("examples/", "templates/")):
            return "private local config"
        if "runtime/hooks/outbox" in rel_path or "hooks/outbox" in rel_path:
            return "hook outbox payload"
        transcript_parts = Path(normalized).parts
        if any(left == "chat" and right == "transcripts" for left, right in zip(transcript_parts, transcript_parts[1:])):
            return "local chat transcript"
        return None

    def release_git_dirty_path(self, status_line: str) -> tuple[str, str]:
        status = status_line[:2]
        path = status_line[3:].replace("\\", "/") if len(status_line) > 3 else ""
        return status, path

    def release_git_dirty_is_allowed_projection(self, status_line: str) -> bool:
        status, path = self.release_git_dirty_path(status_line)
        return status in {" M", "M ", "MM"} and path in RELEASE_ALLOWED_PROJECTION_DIRTY_PATHS

    def forbidden_powershell_reference(self, text: str) -> bool:
        """Reject unsupported wrapper references; prose semantics need source review."""
        return ".ps1" in text.lower()
