import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

base = Path(__file__).resolve().parent
root = base.parents[2]
commands = [["tools/smoke_diagnostics.py"], ["tools/validate-process-forge-schemas.py"],
            ["tools/validate-public-cleanliness.py"], ["tools/validate-process-forge-checksums.py", "--write"],
            ["tools/validate-process-forge-checksums.py", "--check"],
            ["tools/processforge.py", "diagnostics-export", "--project-root", str(root),
             "--output", str(base / "sanitized-diagnostic-bundle-accepted.json")]]
report = {"started_at": datetime.now(timezone.utc).isoformat(), "checks": []}
for command in commands:
    started = time.perf_counter()
    result = subprocess.run([sys.executable, "-B", *command], cwd=root, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=240)
    report["checks"].append({"command": command, "exit_code": result.returncode, "stdout": result.stdout,
                             "stderr": result.stderr, "seconds": round(time.perf_counter() - started, 3)})
    (base / "accepted-revision-checks.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(command[0], result.returncode, flush=True)
report["source_sha256"] = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in
                         ("src/processforge_core/diagnostics.py", "tools/processforge.py", "tools/smoke_diagnostics.py",
                          "tools/smoke_diagnostics_process_invariance.py")}
report["finished_at"] = datetime.now(timezone.utc).isoformat()
(base / "accepted-revision-checks.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
raise SystemExit(0 if all(check["exit_code"] == 0 for check in report["checks"]) else 1)
