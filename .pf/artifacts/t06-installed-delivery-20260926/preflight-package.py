from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
CANDIDATE=ROOT/'.pf/tmp/t06-installed-delivery-20260926/candidate'
INSTALLED=Path('D:/.agents/processforge')
WORKPLACE=Path('D:/.agents/processforge-workplace')
build=json.loads((HERE/'candidate-build.json').read_text())
archive=Path(build['archive'])
assert hashlib.sha256(archive.read_bytes()).hexdigest()==build['archive_sha256']
commands={
 'archive-validation':[sys.executable,'-B',str(CANDIDATE/'bin/pf.py'),'release-archive-test','--archive',str(archive),'--root',str(CANDIDATE),'--extracted-test','quick'],
 'core-update-plan':[sys.executable,'-B',str(CANDIDATE/'bin/pf.py'),'core-update','plan','--core-root',str(INSTALLED),'--archive',str(archive),'--workplace-root',str(WORKPLACE)],
 'runtime-before-status':[sys.executable,'-B',str(INSTALLED/'bin/pf.py'),'runtime','status','--workplace',str(WORKPLACE),'--json'],
 'runtime-before-doctor':[sys.executable,'-B',str(INSTALLED/'bin/pf.py'),'runtime','doctor','--workplace',str(WORKPLACE)],
 'installed-before-status':[sys.executable,'-B',str(CANDIDATE/'bin/pf.py'),'core-update','status','--core-root',str(INSTALLED)],
}
def run(item):
 name,argv=item; start=time.monotonic()
 proc=subprocess.run(argv,cwd=CANDIDATE,capture_output=True,text=True,encoding='utf-8',timeout=600 if name=='archive-validation' else 180)
 row={'time_utc':datetime.now(timezone.utc).isoformat(),'argv':argv,'exit_code':proc.returncode,
      'seconds':round(time.monotonic()-start,3),'stdout':proc.stdout,'stderr':proc.stderr}
 (HERE/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
 return name,row
with ThreadPoolExecutor(max_workers=3) as pool:
 for future in as_completed([pool.submit(run,item) for item in commands.items()]):
  name,row=future.result(); print(name,row['exit_code'],row['seconds'],flush=True)
  if row['exit_code']: print(row['stdout'][-1800:]+row['stderr'][-1800:],flush=True)
