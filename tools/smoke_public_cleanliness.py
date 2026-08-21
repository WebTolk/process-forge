"""Regression proof for public-cleanliness path semantics and fixtures."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "validate-public-cleanliness.py"
RELEASEIGNORE = """.idea/
.serena/
.pf/process-forge.local.yaml
.pf/runtime/
.pf/artifacts/
.pf/reviews/
.pf/handoffs/
.pf/runs/
.pf/contexts/
.pf/assignments/
.pf/dogfooding/
.pf/private-notes/
.pf/cache/
/задания
tools/__pycache__/
*.pyc
"""


def run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(VALIDATOR), "--root", str(root)], text=True, encoding="utf-8", errors="replace", capture_output=True, check=False)


def require(result: subprocess.CompletedProcess[str], expected: int, label: str) -> None:
    if result.returncode != expected:
        raise AssertionError(f"{label}: expected {expected}, got {result.returncode}: {result.stdout}{result.stderr}")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="processforge-public-cleanliness-") as temp:
        root = Path(temp)
        (root / "tools").mkdir()
        (root / ".processforge-releaseignore").write_text(RELEASEIGNORE, encoding="utf-8")
        # public-cleanliness: allow-private-path-fixture
        (root / "tools" / "smoke_security_fixture.py").write_text(
            "# public-cleanliness: allow-private-path-fixture\n"
            "UNSAFE_FIXTURE = 'C:\\\\Users\\\\private'\n"
            "MESSAGE = 'STDOUT:\\n'\n",
            encoding="utf-8",
        )
        require(run(root), 0, "acknowledged fixture and escaped newline")
        # public-cleanliness: allow-private-path-fixture
        (root / "README.md").write_text("local path: C:\\Users\\real-user\n", encoding="utf-8")
        result = run(root)
        require(result, 1, "real public path")
        if "README.md: forbidden private/local path pattern" not in result.stdout:
            raise AssertionError(result.stdout)
        (root / "README.md").unlink()
        # public-cleanliness: allow-private-path-fixture
        (root / "tools" / "smoke_security_fixture.py").write_text("LEAK = 'C:\\\\Users\\\\real-user'\n", encoding="utf-8")
        result = run(root)
        require(result, 1, "unacknowledged Python literal")
        if "tools/smoke_security_fixture.py: forbidden private/local path pattern" not in result.stdout:
            raise AssertionError(result.stdout)
    print("PASS: public-cleanliness fixture semantics smoke")


if __name__ == "__main__":
    main()
