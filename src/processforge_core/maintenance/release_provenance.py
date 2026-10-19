"""Release Git provenance: existing algorithms owned by Core."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import re
import subprocess
from typing import Any

from processforge_core.maintenance.release_sources import ReleaseSourcePolicy

HEX40_RE = re.compile(r"^[0-9a-f]{40}$")

ZIP_MINIMUM_EPOCH = 315532800


class ReleaseGitProvenance:
    def __init__(self, source_policy: ReleaseSourcePolicy) -> None:
        self._source_policy = source_policy

    def git_release_output(self, root: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise SystemExit(f"FAIL: git {' '.join(args)} failed: {detail}")
        return result.stdout.rstrip("\r\n")

    def release_git_provenance(self, root: Path) -> dict[str, Any]:
        if not (root / ".git").exists():
            raise SystemExit("FAIL: release-pack requires a Git source checkout for release manifest provenance")
        dirty = self.git_release_output(root, "status", "--porcelain=v1", "--untracked-files=all").splitlines()
        blocking_dirty = [line for line in dirty if not self._source_policy.release_git_dirty_is_allowed_projection(line)]
        if blocking_dirty:
            sample = ", ".join(line.strip() for line in blocking_dirty[:20])
            suffix = f"; +{len(blocking_dirty) - 20} more" if len(blocking_dirty) > 20 else ""
            raise SystemExit(f"FAIL: release-pack requires clean git source before publishing: {sample}{suffix}")
        commit = self.git_release_output(root, "rev-parse", "HEAD")
        tree = self.git_release_output(root, "rev-parse", "HEAD^{tree}")
        if not HEX40_RE.fullmatch(commit) or not HEX40_RE.fullmatch(tree):
            raise SystemExit("FAIL: release-pack could not capture valid git commit/tree provenance")
        commit_epoch_text = self.git_release_output(root, "show", "-s", "--format=%ct", "HEAD")
        try:
            commit_epoch = int(commit_epoch_text)
        except ValueError as exc:
            raise SystemExit(f"FAIL: invalid git commit timestamp: {commit_epoch_text}") from exc
        source_epoch_text = os.environ.get("SOURCE_DATE_EPOCH")
        if source_epoch_text:
            try:
                source_epoch = int(source_epoch_text)
            except ValueError as exc:
                raise SystemExit(f"FAIL: invalid SOURCE_DATE_EPOCH: {source_epoch_text}") from exc
        else:
            source_epoch = commit_epoch
        if source_epoch < ZIP_MINIMUM_EPOCH:
            raise SystemExit("FAIL: release-pack source date is before the ZIP timestamp lower bound 1980-01-01")
        generated_at = datetime.fromtimestamp(source_epoch, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        return {
            "source_date_epoch": source_epoch,
            "generated_at": generated_at,
            "source": {
                "vcs": "git",
                "commit": commit,
                "tree": tree,
                "dirty": False,
            },
        }
