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
.pf/
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
        for name in ["AGENTS.md", "process-forge.yaml", "hooks.yaml", "contexts/private.yaml"]:
            private_file = root / ".pf" / name
            private_file.parent.mkdir(parents=True, exist_ok=True)
            # public-cleanliness: allow-private-path-fixture
            private_file.write_text("local path: C:\\Users\\real-user\nplatform.private-product\n", encoding="utf-8")
        require(run(root), 0, "private root .pf is outside public validation")
        for name in ["AGENTS.md", "CONTRIBUTING.md", "CONTRIBUTING.ru.md", "README.md", "README.ru.md", "QUICKSTART.md", "QUICKSTART.ru.md"]:
            # public-cleanliness: allow-private-path-fixture
            (root / name).write_text("local path: C:\\Users\\real-user\n", encoding="utf-8")
            result = run(root)
            require(result, 1, f"real public path in {name}")
            if f"{name}: forbidden private/local path pattern" not in result.stdout:
                raise AssertionError(result.stdout)
            (root / name).unlink()
        # public-cleanliness: allow-private-path-fixture
        (root / "tools" / "smoke_security_fixture.py").write_text("LEAK = 'C:\\\\Users\\\\real-user'\n", encoding="utf-8")
        result = run(root)
        require(result, 1, "unacknowledged Python literal")
        if "tools/smoke_security_fixture.py: forbidden private/local path pattern" not in result.stdout:
            raise AssertionError(result.stdout)
    print("PASS: public-cleanliness fixture semantics smoke")


if __name__ == "__main__":
    main()
