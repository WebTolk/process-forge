"""Private exact-scope verification and recorded focused assurance."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import ast, difflib, hashlib, importlib.util, json, re, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
def write_once(path, text):
    if path.exists():
        assert path.read_text(encoding='utf-8')==text, 'Frozen implementation evidence differs'
    else:
        path.write_text(text,encoding='utf-8')
baseline=json.loads((HERE/'baseline.json').read_text())
spec=importlib.util.spec_from_file_location('inventory',ROOT/'tools/validate-process-forge-checksums.py');inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
current={p.relative_to(ROOT).as_posix():p for p in inv.public_files(ROOT)+[ROOT/'checksums/processforge.sha256']}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=baseline['public_sha256'];scope=set(baseline['scope'])
changed={n for n,p in current.items() if n not in old or sha(p)!=old[n]}
assert changed<=scope and not(set(old)-set(current)),changed-scope
tree=ast.parse((ROOT/'tools/processforge.py').read_text(encoding='utf-8'))
assert ast.dump(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='append_process_event'))==baseline['protected_journal_function_ast']
patches=[]
for name in sorted(changed):
    p=ROOT/name
    if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8-sig'))
    if p.suffix=='.md':
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if not link.startswith(('http:','https:','#')):assert (p.parent/link.split('#')[0]).exists(),link
    previous=HERE/'originals'/name
    patches.extend(difflib.unified_diff(previous.read_text(encoding='utf-8').splitlines(True) if previous.exists() else [],p.read_text(encoding='utf-8').splitlines(True),fromfile='before/'+name,tofile='after/'+name))
write_once(HERE/'scoped.patch',''.join(patches))
report={'changed_files':sorted(changed),'unchanged_public_files':len(old)-len(changed.intersection(old)),'source_sha256':{n:sha(p) for n,p in current.items()},'journal_ast_preserved':True}
write_once(HERE/'implementation.json',json.dumps(report,indent=2)+'\n')
write_once(HERE/'implementation.md','# Implementation\n\nImplemented bounded Core metrics and Runtime publication/monitor projection, negotiated server operator controls with fresh worker and request/scheduler admission guard, portable launchers, atomic diagnostics profile plan/apply, schemas and EN/RU documentation.\n\nExact changed paths and all source hashes: implementation.json. '+str(len(changed))+' paths within the declared 20-path scope; unrelated '+str(report['unchanged_public_files'])+' existing public files unchanged. Protected journal append function AST is unchanged. Existing monitor smoke and new metrics/profile/HTTP smokes have passed; full focused assurance follows. Source is not yet the installed build.\n\nSee scoped.patch. No native tray/remote web or host-owned MCP restart claim. User T07 authorization is recorded separately in scope-steering-t07.md and remains the next Work.\n')
if '--prepare' in sys.argv:sys.exit(0)
checks={name:[ROOT/'tools'/('smoke_'+name+'.py')] for name in ['runtime_metrics','server_operator','diagnostics_configure','runtime_monitor','diagnostics','diagnostics_process_invariance','process_event_concurrency','runtime_singleton_orphan','runtime_status_version_truth','runtime_scheduler_failure_isolation','runtime_no_domain_file_patterns','docs_agent_no_manual_infra','docs_mcp_host_owned_stdio','docs_codex_hooks_optional']}
checks.update({'schemas':[ROOT/'tools/validate-process-forge-schemas.py'],'checksums':[ROOT/'tools/validate-process-forge-checksums.py','--check'],'public-cleanliness':[ROOT/'tools/validate-public-cleanliness.py']})
def run(item):
    name,args=item;start=time.monotonic();command=[sys.executable,'-B',*map(str,args)]
    p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=240)
    row={'command':command,'exit_code':p.returncode,'seconds':round(time.monotonic()-start,3),'stdout':p.stdout,'stderr':p.stderr}
    (HERE/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
    return name,row
results={}
with ThreadPoolExecutor(max_workers=3) as pool:
    for future in as_completed([pool.submit(run,x) for x in checks.items()]):
        name,row=future.result();results[name]=row;print(name,row['exit_code'],flush=True)
assert all(r['exit_code']==0 for r in results.values()),[(n,r['stdout'][-1600:],r['stderr'][-1600:]) for n,r in results.items() if r['exit_code']]
diff=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True);assert diff.returncode==0,diff.stdout+diff.stderr
assert all(sha(ROOT/n)==h for n,h in report['source_sha256'].items())
report.update(status='PASS',checks={n:r['exit_code'] for n,r in results.items()})
(HERE/'assurance-results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('PASS focused source assurance',flush=True)
