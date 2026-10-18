"""Focused independent checks and exact public-payload scope preservation."""
from concurrent.futures import ThreadPoolExecutor,as_completed
import ast,difflib,hashlib,importlib.util,json,re,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
scope={'tools/processforge.py','tools/smoke_process_event_concurrency.py','docs/concepts/session-telemetry.md','docs/ru/concepts/session-telemetry.md','checksums/processforge.sha256'}
baseline=json.loads((HERE/'baseline.json').read_text())
spec=importlib.util.spec_from_file_location('inventory',ROOT/'tools/validate-process-forge-checksums.py');inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
current={p.relative_to(ROOT).as_posix():p for p in inv.public_files(ROOT)+[ROOT/'checksums/processforge.sha256']}
changed={n for n,p in current.items() if n not in baseline or hashlib.sha256(p.read_bytes()).hexdigest()!=baseline[n]}
assert changed==scope and not(set(baseline)-set(current)),changed
for name in scope:
    p=ROOT/name
    if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8-sig'))
    if p.suffix=='.md':
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if not link.startswith(('http:','https:','#')):assert (p.parent/link.split('#')[0]).exists(),link
patches=[]
for name in sorted(scope):
    old=HERE/'originals'/name
    patches.extend(difflib.unified_diff(old.read_text(encoding='utf-8').splitlines(True) if old.exists() else [],(ROOT/name).read_text(encoding='utf-8').splitlines(True),fromfile='before/'+name,tofile='after/'+name))
(HERE/'scoped.patch').write_text(''.join(patches),encoding='utf-8')
fixture=ROOT/'.pf/tmp/event-journal-repair-20260926/public-fixture';assert not fixture.exists()
for name,p in inv.public_file_entries(ROOT)+[('checksums/processforge.sha256',ROOT/'checksums/processforge.sha256')]:
    target=fixture/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(inv.released_content(p))
checks={
    'central-ingress':[ROOT/'tools/smoke_central_event_ingress.py'],
    'central-replay':[ROOT/'tools/smoke_central_event_replay.py'],
    'stage-events':[ROOT/'tools/smoke_work_transition_emits_stage_events.py'],
    'registry-lock':[ROOT/'tools/smoke_cli_audit_f0608.py'],
    'fixture-schemas':[fixture/'tools/validate-process-forge-schemas.py','--root',fixture],
    'checksums':[ROOT/'tools/validate-process-forge-checksums.py','--check'],
    'public-cleanliness':[ROOT/'tools/validate-public-cleanliness.py'],
}
def run(item):
    name,args=item;start=time.monotonic();command=[sys.executable,'-B',*map(str,args)]
    p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=240)
    row={'command':command,'exit_code':p.returncode,'seconds':round(time.monotonic()-start,3),'stdout':p.stdout,'stderr':p.stderr}
    (HERE/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
    return name,row
results={}
with ThreadPoolExecutor(max_workers=3) as pool:
    for f in as_completed([pool.submit(run,x) for x in checks.items()]):
        name,row=f.result();results[name]=row;print(name,row['exit_code'],flush=True)
assert all(r['exit_code']==0 for r in results.values()),[(n,r['stdout'][-1500:],r['stderr'][-1500:]) for n,r in results.items() if r['exit_code']]
diff=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True);assert diff.returncode==0,diff.stdout+diff.stderr
report={'status':'PASS','changed_files':sorted(changed),'unchanged_public_files':len(baseline)-len(scope.intersection(baseline)),
        'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in scope},'checks':{n:r['exit_code'] for n,r in results.items()},
        'concurrency_and_private_repair_tests':'previously executed PASS, see green-observation.md; same tested code retained',
        'live_journal':'not yet repaired; expected single historical invalid fragment preserved',
        'public_fixture':'durable non-release validation input; not an installable archive'}
(HERE/'assurance-results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report),flush=True)
