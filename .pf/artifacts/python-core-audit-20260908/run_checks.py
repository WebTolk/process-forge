"""Run existing isolated checks and preserve exact output for this audit."""
import concurrent.futures
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).parent/'checks'
OUT.mkdir(exist_ok=True)
NAMES=[
 'smoke_core_update_manifest.py',
 'smoke_project_resource_narrowing_search.py',
 'smoke_workplace_search_index.py',
 'smoke_garage_cross_project_security.py',
 'smoke_garage_no_hooks_sessionless.py',
 'smoke_work_transition_recovers_after_invalid_evidence.py',
 'smoke_work_transition_final_stage_completes_run.py',
 'smoke_process_run_task_batch.py',
 'smoke_central_event_ingress_kernel.py',
 'validate-process-forge-schemas.py',
 'validate-process-forge-checksums.py',
 'validate-public-cleanliness.py',
]
def run(name):
 start=time.monotonic(); command=[sys.executable,str(ROOT/'tools'/name)]
 try:
  p=subprocess.run(command,cwd=ROOT,text=True,encoding='utf-8',errors='replace',capture_output=True,timeout=420)
  code=p.returncode; output=p.stdout+p.stderr
 except subprocess.TimeoutExpired as exc:
  code='timeout'; output=str(exc)
 (OUT/(name+'.txt')).write_text(output,encoding='utf-8')
 return {'check':name,'command':command,'exit_code':code,'seconds':round(time.monotonic()-start,2),'output':str((OUT/(name+'.txt')).relative_to(ROOT))}
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for f in concurrent.futures.as_completed([pool.submit(run,n) for n in NAMES]):
  result=f.result();results.append(result);print(json.dumps(result),flush=True)
  (OUT/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
