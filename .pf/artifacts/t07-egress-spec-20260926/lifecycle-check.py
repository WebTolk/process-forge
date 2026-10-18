"""Read-only T07 lifecycle verification using installed PF CLI."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN = "garage-t07-pf-vision-alignment-r02-specify-provider-neutral-local-filter"
TASK = "t07-pf-vision-alignment-r02-specify-provider-neutral-local-filtering-of"
phase = sys.argv[1]
assert phase in {"assurance", "final"}
target = HERE / ("lifecycle-" + phase + ".json")
assert not target.exists(), "Preserve recorded verification; use a new evidence filename for another observation"
run = yaml.safe_load((ROOT / ".pf/runs" / RUN / "run.yaml").read_text(encoding="utf-8"))
task = yaml.safe_load((ROOT / ".pf/assignments" / (TASK + ".yaml")).read_text(encoding="utf-8"))
capsule = ROOT / task["process_execution"]["assignment_capsule"]
digest = hashlib.sha256(capsule.read_bytes()).hexdigest()
assert digest == "698a17753a3677a9d2e158806d3331e1df4585ca65134a94598fe73929bf888d"
assert task["process_execution"]["assignment_capsule_checksum"] == "sha256:" + digest
history = task["stage_history"]
expected = ["orchestration", "intake-scope", "investigation", "domain-modeling", "architecture-plan", "implementation", "code-assurance", "release-delivery", "evolve"]
assert [stage["stage_id"] for stage in history] == (expected if phase == "final" else expected[:6])
assert all(stage["status"] == "completed" and stage["outcome"] == "completed" and stage["notes"].strip() for stage in history)
assert run["status"] == ("completed" if phase == "final" else "in_progress")
assert task["status"] == ("done" if phase == "final" else "in_progress")
if phase == "assurance":
    assert task["stage"] == "code-assurance"
evidence = {}
records = 0
for stage in history:
    for item in stage["evidence"]:
        if item.get("path") and item.get("sha256"):
            path = ROOT / item["path"]
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            assert item["sha256"] == "sha256:" + actual, item
            evidence[item["path"]] = actual
            records += 1
command = [sys.executable, "-B", "D:/.agents/processforge/bin/pf.py", "run-doctor", "--project-root", str(ROOT), "--run", RUN]
doctor = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=180)
result = {"recorded_at": datetime.now(timezone.utc).isoformat(), "phase": phase, "run": RUN,
          "run_status": run["status"], "assignment_status": task["status"], "capsule_sha256": digest,
          "completed_stages": [s["stage_id"] for s in history], "stage_evidence_records": records,
          "evidence_hashes": evidence, "doctor": {"argv": command, "exit_code": doctor.returncode,
          "stdout": doctor.stdout, "stderr": doctor.stderr}, "doctor_passes": sum(line.startswith("PASS:") for line in doctor.stdout.splitlines()),
          "status": "PASS" if doctor.returncode == 0 else "FAIL"}
target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: result[k] for k in ["status", "phase", "run_status", "doctor_passes", "stage_evidence_records", "completed_stages"]}))
assert doctor.returncode == 0
