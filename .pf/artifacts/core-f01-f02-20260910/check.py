"""Capture real command output, exit and timing without shell interpolation."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
label, *command = sys.argv[1:]
if command and command[0] == '--':
    command.pop(0)
if command[0] == 'python':
    command[0] = sys.executable
started = datetime.now(timezone.utc).isoformat()
clock = time.monotonic()
env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
with (OUT / (label + '.stdout.txt')).open('w', encoding='utf-8') as stdout, (OUT / (label + '.stderr.txt')).open('w', encoding='utf-8') as stderr:
    result = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
payload = dict(command=command, started_at=started, elapsed_seconds=round(time.monotonic()-clock, 3), exit_code=result.returncode, stdout=label+'.stdout.txt', stderr=label+'.stderr.txt')
(OUT / (label + '.json')).write_text(json.dumps(payload, indent=2)+'\n', encoding='utf-8')
print(json.dumps(payload))
sys.exit(result.returncode)
