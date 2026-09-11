import json,subprocess,sys
from pathlib import Path
sys.path.insert(0,'tools')
from processforge_subprocess import run_command
out=Path('.pf/artifacts/publish-f06-f08-20260910')
results=[]
for i in range(3):
 r=run_command([sys.executable,'-u','.pf/tmp/runtime-diagnose.py'],cwd=Path.cwd(),timeout=180)
 (out/f'runtime-diagnose-repeat-{i}.txt').write_text(r.stdout+r.stderr,encoding='utf-8')
 results.append({'attempt':i,'exit':r.returncode});print(json.dumps(results[-1]),flush=True)
 if r.returncode:break
(out/'runtime-diagnose-repeats.json').write_text(json.dumps(results,indent=2))
