"""Capture the pre-repair hook failure; no infrastructure or project writes."""
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[3]
env = dict(os.environ, PF_CODEX_HOOK_DEBUG="1")
script = '''import sys;sys.path.insert(0,"tools");from pf_runtime import codex_hooks as h
def fail(payload): raise OSError("synthetic failure")
h.dispatch=fail
raise SystemExit(h.main())
'''
cases = {}
for name, command, payload in (
    ("malformed_input", [sys.executable, "-B", "tools/pf_runtime/codex_hooks.py"], "invalid-json"),
    ("stop_dispatch_failure", [sys.executable, "-B", "-c", script], json.dumps({"hook_event_name": "Stop"})),
):
    result = subprocess.run(command, cwd=root, env=env, input=payload, text=True, capture_output=True, timeout=20)
    cases[name] = {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
out = Path(__file__).with_name("hook-stdout-before.json")
out.write_text(json.dumps(cases, indent=2), encoding="utf-8")
assert all('"reason"' in case["stdout"] for case in cases.values()), cases
assert all(not case["stderr"] for case in cases.values()), cases
print("REPRODUCED: diagnostics contaminate hook failure stdout; Stop neutral response absent")
