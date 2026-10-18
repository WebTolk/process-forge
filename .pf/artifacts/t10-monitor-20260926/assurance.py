"""Scoped checks; preserve the live-journal failure separately from product QA."""
import ast,hashlib,importlib.util,json,re,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
OUT=HERE/'assurance-results.json'
assert not OUT.exists()
result={'started_at':datetime.now(timezone.utc).isoformat(),'checks':[]}
def save():OUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
def run(label,args,root=ROOT,timeout=180,expected=0):
 start=time.monotonic()
 p=subprocess.run([sys.executable,'-B',*map(str,args)],cwd=root,capture_output=True,text=True,encoding='utf-8',timeout=timeout)
 item={'id':label,'command':list(map(str,args)),'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'seconds':round(time.monotonic()-start,3)}
 result['checks'].append(item);save();print(label,p.returncode,flush=True)
 assert p.returncode==expected,(label,p.stdout,p.stderr)
 return p
paths=['tools/pf_runtime/monitor.py','tools/pf_runtime/service.py','tools/processforge.py','tools/smoke_runtime_monitor.py','docs/concepts/runtime-monitor.md','docs/ru/concepts/runtime-monitor.md','docs/concepts/runtime-mcp.md','docs/ru/concepts/runtime-mcp.md','checksums/processforge.sha256']
for name in paths:
 p=ROOT/name
 if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8-sig'),filename=name)
 if p.suffix=='.md':
  body=p.read_text(encoding='utf-8');assert '\ufffd' not in body
  for link in re.findall(r'\]\(([^)]+)\)',body):
   if not link.startswith(('http:','https:','#')):assert (p.parent/link.split('#')[0]).exists(),(name,link)
result['ast_and_links']='PASS'
for name in ['smoke_runtime_monitor','smoke_runtime_singleton_orphan','smoke_runtime_status_version_truth','smoke_runtime_scheduler_failure_isolation','smoke_runtime_no_domain_file_patterns','smoke_docs_agent_no_manual_infra','smoke_docs_mcp_host_owned_stdio','smoke_docs_codex_hooks_optional']:
 run(name,[ROOT/'tools'/(name+'.py')])
run('public-cleanliness',[ROOT/'tools/validate-public-cleanliness.py'])
run('checksums',[ROOT/'tools/validate-process-forge-checksums.py','--check'])
event=ROOT/'.pf/runtime/events/events.ndjson'
bad=event.read_text(encoding='utf-8-sig').splitlines()[34211]
assert hashlib.sha256(bad.encode()).hexdigest()=='6f1fa1694252d1b08e1ac8351716ab6129f302a26135c6bd56d7b1466c088739'
result['preexisting_journal_finding']={'path':'.pf/runtime/events/events.ndjson','line':34212,'sha256':hashlib.sha256(bad.encode()).hexdigest(),'embedded_time':'2026-09-26T12:15:42','preserved':True}
p=run('checkout-schemas-known-journal-failure',[ROOT/'tools/validate-process-forge-schemas.py'],expected=1)
assert ':34212 invalid NDJSON: Extra data:' in p.stdout+p.stderr
spec=importlib.util.spec_from_file_location('inventory',ROOT/'tools/validate-process-forge-checksums.py')
inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
fixture=ROOT/'.pf/tmp/t10-monitor-20260926/public-fixture'
assert not fixture.exists()
entries=inv.public_file_entries(ROOT)
for name,source in entries:
 target=fixture/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(inv.released_content(source))
target=fixture/'checksums/processforge.sha256';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(inv.released_content(ROOT/'checksums/processforge.sha256'))
result['public_fixture']={'path':fixture.relative_to(ROOT).as_posix(),'files':len(entries)+1,'kind':'non-release product validation input, not an installable release archive'}
save()
run('public-fixture-schemas',[fixture/'tools/validate-process-forge-schemas.py','--root',fixture],root=fixture)
run('public-fixture-checksums',[fixture/'tools/validate-process-forge-checksums.py','--root',fixture,'--check'],root=fixture)
run('public-fixture-monitor',[fixture/'tools/smoke_runtime_monitor.py'],root=fixture)
run('preservation',[HERE/'preservation.py'])
diff=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
assert diff.returncode==0,(diff.stdout,diff.stderr)
result['diff_check']={'exit_code':diff.returncode,'stdout':diff.stdout,'stderr':diff.stderr}
result['source_hashes']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths}
result['finished_at']=datetime.now(timezone.utc).isoformat()
result['status']='PASS_with_preexisting_live_journal_finding'
save();print(result['status'],flush=True)
