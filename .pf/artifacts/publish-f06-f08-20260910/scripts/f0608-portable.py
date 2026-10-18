import json,subprocess,sys,tempfile,zipfile
from pathlib import Path
out=Path('.pf/artifacts/publish-f06-f08-20260910').resolve(); results=[]
with tempfile.TemporaryDirectory(prefix='pf-f0608-public-') as temp:
 root=Path(temp)
 with zipfile.ZipFile(out/'processforge-5c95391.zip') as z:z.extractall(root)
 cli=root/'tools/processforge.py';original=cli.read_bytes()
 cli.write_bytes(Path('tools/processforge.py').read_bytes())
 (root/'tools/smoke_cli_audit_f0608.py').write_bytes(Path('tools/smoke_cli_audit_f0608.py').read_bytes())
 for name,baseline in [('public',False),('baseline',True)]:
  if baseline:cli.write_bytes(original)
  p=subprocess.run([sys.executable,str(root/'tools/smoke_cli_audit_f0608.py')],cwd=root,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
  (out/f'f0608-{name}.txt').write_text(p.stdout+p.stderr)
  results.append({'case':name,'exit':p.returncode});print(json.dumps(results[-1]),flush=True)
(out/'f0608-portable.json').write_text(json.dumps(results,indent=2))
assert results[0]['exit']==0 and results[1]['exit']!=0
