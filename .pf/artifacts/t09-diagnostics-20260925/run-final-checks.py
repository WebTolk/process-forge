import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[3]
commands = [
    ["tools/smoke_diagnostics.py"],
    ["tools/smoke_runtime_ledger_hooks_mcp.py"],
    ["tools/smoke_central_event_ingress.py"],
    ["tools/smoke_processforge_core_package_bootstrap.py"],
    ["tools/validate-public-cleanliness.py"],
    ["tools/validate-process-forge-checksums.py", "--write"],
    ["tools/validate-process-forge-checksums.py", "--check"],
]
report = {"started_at": datetime.now(timezone.utc).isoformat(), "checks": []}
for command in commands:
    start = time.perf_counter()
    result = subprocess.run([sys.executable, "-B", *command], cwd=root, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=240)
    report["checks"].append({"command": command, "exit_code": result.returncode, "stdout": result.stdout,
                             "stderr": result.stderr, "seconds": round(time.perf_counter() - start, 3)})
    Path(__file__).with_name("final-checks.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(command, result.returncode, flush=True)
report["source_sha256"] = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (
    root / "src/processforge_core/diagnostics.py", root / "tools/processforge.py", root / "tools/smoke_diagnostics.py")}
report["finished_at"] = datetime.now(timezone.utc).isoformat()
Path(__file__).with_name("final-checks.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
raise SystemExit(0 if all(check["exit_code"] == 0 for check in report["checks"]) else 1)
