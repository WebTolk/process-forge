import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
allowed={'tools/pf_runtime/monitor.py','tools/pf_runtime/service.py','tools/processforge.py','tools/smoke_runtime_monitor.py','docs/concepts/runtime-monitor.md','docs/ru/concepts/runtime-monitor.md','docs/concepts/runtime-mcp.md','docs/ru/concepts/runtime-mcp.md','checksums/processforge.sha256'}
old=json.loads((HERE/'baseline.json').read_text(encoding='utf-8'))['files']
changed=[p for p,h in old.items() if p not in allowed and (not (ROOT/p).is_file() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h)]
listed=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
added=[p for p in listed if p and not p.startswith('.pf/') and p not in old and p not in allowed and (ROOT/p).is_file()]
result={'status':'FAIL' if changed or added else 'PASS','baseline_files':len(old),'unexpected_changed':changed,'unexpected_added':added,'allowed_changes':sorted(allowed)}
(HERE/'preservation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
assert not changed and not added
