import hashlib,json,subprocess,sys,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
out=Path('.pf/artifacts/publish-f06-f08-20260910'); root=Path(r'D:\.agents\processforge'); wp=Path(r'D:\.agents\processforge-workplace')
before=json.loads((out/'workplace-before.json').read_text())
changed=[p for p,h in before.items() if not (wp/p).is_file() or hashlib.sha256((wp/p).read_bytes()).hexdigest()!=h]
(out/'workplace-preservation.json').write_text(json.dumps({'checked':len(before),'changed':changed,'result':'PASS' if not changed else 'FAIL'},indent=2))
jobs=[('installed-checksum',['tools/validate-process-forge-checksums.py','--root',str(root),'--check']),('installed-update-doctor',['bin/pf.py','update','doctor','--workplace',str(wp)]),('installed-search-smoke',['tools/smoke_workplace_search_index.py']),('installed-evidence-smoke',['tools/smoke_work_evidence_freshness.py']),('installed-completion-smoke',['tools/smoke_work_completion_recovery.py'])]
def run(item):
    name,args=item;t=time.monotonic()
    p=subprocess.run([sys.executable,str(root/args[0]),*args[1:]],cwd=root,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=900)
    (out/(name+'.txt')).write_text(p.stdout+p.stderr,encoding='utf-8')
    record={'name':name,'exit':p.returncode,'seconds':round(time.monotonic()-t,2)}
    (out/(name+'.json')).write_text(json.dumps(record));print(json.dumps(record),flush=True)
    return record
with ThreadPoolExecutor(max_workers=3) as pool: results=list(pool.map(run,jobs))
(out/'installed-tests.json').write_text(json.dumps(results,indent=2))
raise SystemExit(1 if changed or any(x['exit'] for x in results) else 0)
