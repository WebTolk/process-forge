"""Reproduce broad-suite Runtime startup failure on exact tracked public HEAD."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
revision=json.loads((OUT/'baseline.json').read_text(encoding='utf-8'))['head']
archive=subprocess.check_output(['git','archive','--format=tar',revision],cwd=ROOT)
with tempfile.TemporaryDirectory(prefix='pf-f0102-baseline-runtime-') as raw:
    copy=Path(raw)/'public'; copy.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive),mode='r:') as tar:
        members=[m for m in tar.getmembers() if not m.name.startswith(('.pf/','.codex/','dist/')) and m.name not in {'.pf','.codex','dist'}]
        tar.extractall(copy,members=members,filter='data')
    assert not (copy/'.pf').exists() and not (copy/'.git').exists()
    command=[sys.executable,str(copy/'tools/smoke_long_lived_runtime.py')]
    start=time.monotonic()
    try:
        result=subprocess.run(command,cwd=copy,capture_output=True,text=True,encoding='utf-8',errors='replace',env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONUTF8='1'),timeout=300)
        stdout,stderr,code=result.stdout,result.stderr,result.returncode
    except subprocess.TimeoutExpired as exc:
        stdout=(exc.stdout or b'').decode('utf-8','replace') if isinstance(exc.stdout,bytes) else (exc.stdout or '')
        stderr=(exc.stderr or b'').decode('utf-8','replace') if isinstance(exc.stderr,bytes) else (exc.stderr or '')
        code=124
    (OUT/'baseline-runtime.stdout.txt').write_text(stdout,encoding='utf-8')
    (OUT/'baseline-runtime.stderr.txt').write_text(stderr,encoding='utf-8')
    payload=dict(revision=revision,command=command,exit_code=code,elapsed_seconds=round(time.monotonic()-start,3),same_startup_failure='runtime exited during startup with code 1' in stdout+stderr,public_files=sum(m.isfile() for m in members),source='git archive exact baseline public files without .pf/.git')
(OUT/'baseline-runtime.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
print(json.dumps(payload))
