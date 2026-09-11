"""Private orchestrator evidence recorder; command output stays in audit scope."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
parser = argparse.ArgumentParser()
parser.add_argument("label")
parser.add_argument("command", nargs=argparse.REMAINDER)
args = parser.parse_args()
if not args.command or not args.label.replace("-", "").replace("_", "").isalnum():
    parser.error("provide safe label and command")
started = datetime.now(timezone.utc).isoformat()
begin = time.monotonic()
child_env = dict(os.environ, PYTHONIOENCODING="utf-8")
process = subprocess.Popen(args.command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, encoding="utf-8", errors="replace", env=child_env)
lines = []
for line in process.stdout:
    lines.append(line)
    print(line, end="", flush=True)
code = process.wait()
result = {"command": args.command, "started_at": started,
          "finished_at": datetime.now(timezone.utc).isoformat(),
          "elapsed_seconds": round(time.monotonic() - begin, 3), "exit_code": code,
          "output": "".join(lines)}
Path(__file__).with_name(args.label + ".json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
sys.exit(code)
