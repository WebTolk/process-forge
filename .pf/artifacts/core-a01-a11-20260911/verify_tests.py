"""Primary-owned bounded regression runner with durable stdout and metadata."""
from pathlib import Path
import argparse
import io
import json
import shutil
import subprocess
import sys
import time
import zipfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT/'tools'))
from processforge_subprocess import run_command, diagnostic_text

parser=argparse.ArgumentParser()
parser.add_argument('--baseline', action='store_true')
parser.add_argument('--timeout', type=int, default=180)
parser.add_argument('tests', nargs='+')
args=parser.parse_args()
mode='baseline' if args.baseline else 'current'
target=ROOT
if args.baseline:
    target=ROOT/'.pf/tmp/core-a01-a11-baseline'
    if not target.is_dir():
        baseline=json.loads((OUT/'baseline.json').read_text())
        data=subprocess.check_output(['git','archive','--format=zip',baseline['head']],cwd=ROOT)
        target.mkdir(parents=True)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            archive.extractall(target)
results=[]
for name in args.tests:
    filename=name if name.endswith('.py') else name+'.py'
    if args.baseline:
        shutil.copy2(ROOT/'tools'/filename, target/'tools'/filename)
    started=time.monotonic()
    command=[sys.executable,str(target/'tools'/filename)]
    result=run_command(command,cwd=target,timeout=args.timeout)
    elapsed=round(time.monotonic()-started,2)
    folder=OUT/'validation'/mode
    folder.mkdir(parents=True,exist_ok=True)
    if (folder/(Path(filename).stem+'.txt')).exists():
        history=folder/'history'/str(time.time_ns())
        history.mkdir(parents=True)
        for suffix in ('.txt', '.json'):
            previous=folder/(Path(filename).stem+suffix)
            if previous.exists():
                shutil.copy2(previous,history/previous.name)
    (folder/(Path(filename).stem+'.txt')).write_text(diagnostic_text(result),encoding='utf-8')
    metadata={'test':filename,'mode':mode,'returncode':result.returncode,'seconds':elapsed,'command':command}
    (folder/(Path(filename).stem+'.json')).write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    results.append(metadata)
    print(json.dumps(metadata),flush=True)
print('PRIMARY RUN COMPLETE',len(results),flush=True)
raise SystemExit(0 if all((r['returncode'] != 0 if args.baseline else r['returncode']==0) for r in results) else 1)
