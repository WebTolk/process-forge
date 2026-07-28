#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from core_boundary_smoke_helpers import ROOT, write_workplace
from processforge import load_yaml_document


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-platform-create-levels-") as raw:
        workplace = Path(raw) / "workplace"
        write_workplace(workplace)
        (workplace / "packages").mkdir()
        (workplace / "registries" / "package-roots.yaml").write_text(
            """schema_version: 1
package_roots:
  - id: global
    path: packages
    status: available
    default: true
""",
            encoding="utf-8",
        )
        for package_id in ["docs.example-base", "docs.example-child"]:
            (workplace / "packages" / f"{package_id}.yaml").write_text(
                f"""schema_version: 1
id: {package_id}
type: knowledge_package
resources: []
""",
                encoding="utf-8",
            )
        command = [
            sys.executable,
            str(ROOT / "bin" / "pf.py"),
            "platform-create",
            "--workplace",
            str(workplace),
            "--id",
            "platform.example-child",
            "--title",
            "Example Child",
            "--requires-package",
            "docs.example-base",
            "--requires-package",
            "docs.example-child",
            "--recommends-template",
            "example.project-context",
            "--optional-tool",
            "playwright-mcp",
            "--apply",
        ]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=60)
        assert result.returncode == 0, result.stdout + result.stderr
        contract = load_yaml_document(workplace / "platform-contracts" / "platform.example-child" / "platform-contract.yaml")
        assert contract["requires"]["knowledge_packages"] == ["docs.example-base", "docs.example-child"], contract
        assert contract["recommends"]["templates"] == ["example.project-context"], contract
        assert contract["optional"]["tools"] == ["playwright-mcp"], contract
    print("PASS: platform-create include levels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
