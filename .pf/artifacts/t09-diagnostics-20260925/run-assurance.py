import json
from pathlib import Path
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[3]
names = [
    "smoke_diagnostics", "smoke_classifier_distribution_parity", "smoke_mcp_jsonrpc_validation",
    "smoke_mcp_missing_session_diagnostics", "smoke_garage_no_hooks_sessionless",
    "smoke_runtime_ledger_hooks_mcp", "smoke_central_event_ingress",
    "smoke_processforge_core_package_bootstrap", "smoke_worker_run_shell",
    "smoke_worker_environment_secret_redaction", "smoke_codex_exec_worker",
    "smoke_process_execution_integrity", "smoke_process_execution_state_semantics",
    "smoke_multi_process_work_capsule", "validate-public-cleanliness",
]
results = []
for name in names:
    start = time.perf_counter()
    try:
        result = subprocess.run([sys.executable, "-B", str(root / "tools" / (name + ".py"))], cwd=root,
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
        item = dict(name=name, exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
    except subprocess.TimeoutExpired as exc:
        item = dict(name=name, exit_code=-1, timeout=True, stdout=str(exc.stdout), stderr=str(exc.stderr))
    item["seconds"] = round(time.perf_counter() - start, 3)
    results.append(item)
    Path(__file__).with_name("assurance-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(name, item["exit_code"], item["seconds"], flush=True)
print("PASS" if all(item["exit_code"] == 0 for item in results) else "FAIL", flush=True)
raise SystemExit(0 if all(item["exit_code"] == 0 for item in results) else 1)
