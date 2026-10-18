"""Persist audit verification results and preserve the focused release-test report."""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).parent


def main() -> None:
    checks = []
    for args in [
        [sys.executable, "tools/validate-process-forge-schemas.py"],
        [sys.executable, "tools/validate-public-cleanliness.py"],
        [sys.executable, "tools/validate-process-forge-checksums.py", "--check"],
        ["git", "diff", "--check"],
    ]:
        result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        checks.append({"command": args, "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    inventory = json.loads((OUTPUT / "inventory.json").read_text(encoding="utf-8"))
    changed = [item["path"] for item in inventory["documents"]
               if hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() != item["sha256"]]
    for name in ("latest-report.json", "latest-report.md", "latest-trace.ndjson"):
        source = ROOT / ".pf/runtime/release-test" / name
        (OUTPUT / name.replace("latest-", "focused-")).write_bytes(source.read_bytes())
    result = {"verified_at": datetime.now(timezone.utc).isoformat(), "checks": checks,
              "documents_checked_for_changes": len(inventory["documents"]), "changed_documents": changed,
              "status": "PASS" if not changed and all(c["exit_code"] == 0 for c in checks) else "FAIL"}
    (OUTPUT / "validation.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
