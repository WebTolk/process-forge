"""Bounded installed-acceptance correction in the same authorized Work."""
import ast,importlib.util,json,hashlib,subprocess,sys
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
previous=ROOT/'.pf/artifacts/t10-operator-20260926'
scope={'src/processforge_core/runtime_metrics.py','tools/pf_runtime/service.py','tools/smoke_runtime_metrics.py','docs/concepts/runtime-monitor.md','docs/ru/concepts/runtime-monitor.md','checksums/processforge.sha256'}
baseline=json.loads((previous/'build.json').read_text())
spec=importlib.util.spec_from_file_location('inventory',ROOT/'tools/validate-process-forge-checksums.py');inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
files={p.relative_to(ROOT).as_posix():p for p in inv.public_files(ROOT)+[ROOT/'checksums/processforge.sha256']}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
changed={n for n,p in files.items() if sha(p)!=baseline['source_sha256'].get(n)}
assert changed==scope and set(files)==set(baseline['source_sha256']),changed
for n in changed:
    if n.endswith('.py'):ast.parse((ROOT/n).read_text(encoding='utf-8'))
(HERE/'work.py').write_bytes((previous/'work.py').read_bytes())
(HERE/'activity.py').write_bytes((previous/'activity.py').read_bytes())
s=(previous/'build.py').read_text(encoding='utf-8')
s=s.replace("BASE='40c9894227738472976546849047550415099486'", "BASE='a5eeac53c50742f1eb04645d727f03c748c80eb6'")
s=s.replace("OLD=ROOT/'.pf/tmp/t10-installed-delivery-20260926/candidate'", "OLD=ROOT/'.pf/tmp/t10-operator-20260926/candidate'")
s=s.replace("CANDIDATE=ROOT/'.pf/tmp/t10-operator-20260926/candidate'", "CANDIDATE=ROOT/'.pf/tmp/t10-operator-runtime-fix-20260926/candidate'")
start=s.index('EXPECTED=');end=s.index("assert state(",start)
s=s[:start]+"EXPECTED=set(json.loads((HERE/'assurance-results.json').read_text())['changed_files'])\n"+s[end:]
s=s.replace("['stage']['id']=='code-assurance'", "['stage']['id']=='release-delivery'")
s=s.replace('Deliver bounded operator metrics, guarded server controls and journal serialization','Publish bounded Runtime metrics independently of project scheduling')
s=s.replace("['runtime_metrics','server_operator','diagnostics_configure','process_event_concurrency']", "['runtime_metrics','server_operator','runtime_scheduler_failure_isolation']")
s=s.replace("['runtime_metrics','server_operator','diagnostics_configure','runtime_monitor','process_event_concurrency']", "['runtime_metrics','server_operator','runtime_monitor']")
(HERE/'build.py').write_text(s,encoding='utf-8')
s=(previous/'install.py').read_text(encoding='utf-8')
s=s.replace("ROOT/'.pf/tmp/t10-operator-20260926/extracted'", "ROOT/'.pf/tmp/t10-operator-runtime-fix-20260926/extracted'")
s=s.replace("operator=json.loads(command('installed-server-status',cli('server','status','--workplace',WP,'--json')))\nassert operator['metrics'] is not None, operator['issues']", "import time\nfor attempt in range(10):\n    operator=json.loads(command('installed-server-status-'+str(attempt),cli('server','status','--workplace',WP,'--json')))\n    if operator['metrics'] is not None:\n        break\n    time.sleep(1)\nassert operator['metrics'] is not None, operator['issues']")
(HERE/'install.py').write_text(s,encoding='utf-8')
checks=['runtime_metrics','server_operator','runtime_monitor','runtime_scheduler_failure_isolation','runtime_no_domain_file_patterns']
def run(name):
    command=[sys.executable,'-B',str(ROOT/'tools'/('smoke_'+name+'.py'))]
    p=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=120,cwd=ROOT)
    row=dict(argv=command,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)
    (HERE/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
    print(name,p.returncode,flush=True)
    assert p.returncode==0,row
    return name
with ThreadPoolExecutor(max_workers=2) as pool:
    for future in as_completed([pool.submit(run,n) for n in checks]):future.result()
for tool,args in [('validate-process-forge-checksums',['--check']),('validate-public-cleanliness',[])]:
    p=subprocess.run([sys.executable,'-B',str(ROOT/'tools'/(tool+'.py')),*args],capture_output=True,text=True,encoding='utf-8',cwd=ROOT,timeout=120)
    (HERE/(tool+'.json')).write_text(json.dumps(dict(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr),indent=2)+'\n',encoding='utf-8');assert p.returncode==0,p.stdout+p.stderr
assert subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True).returncode==0
report=dict(status='PASS',changed_files=sorted(changed),source_sha256={n:sha(p) for n,p in files.items()},checks=checks,prior_assurance=str(previous/'assurance-results.json'))
(HERE/'assurance-results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
(HERE/'assurance.md').write_text('# Installed acceptance correction assurance\n\nRoot cause and bounded architecture correction: ../t10-operator-20260926/live-acceptance-correction.md. Exact six-file scope preserved; all other source hashes match previously qualified a5eeac53. New real observation-thread regression publishes while ordinary routing is held blocked. Metrics, guarded server, monitor, scheduler isolation, Core boundary, checksum/cleanliness/diff checks pass. Previous 18 source checks remain evidence for unchanged behavior, including five-profile process invariance and concurrent journal append. Candidate/archive and installed acceptance must still pass before completing the existing Work.\n',encoding='utf-8')
print('PASS delivery correction source assurance',flush=True)
