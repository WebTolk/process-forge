from concurrent.futures import ThreadPoolExecutor, as_completed
import ast, fnmatch, importlib.util
from work import *

assert state('assurance-final-start')['stage']['id']=='code-assurance'
first=json.loads((HERE/'assurance-check-results.json').read_text())
previous=set(first['passed'])
scripts=['smoke_egress_engine','smoke_egress_work','smoke_egress_transport','smoke_server_operator']
jobs=[(s,[sys.executable,'-B',ROOT/'tools'/(s+'.py'),*(['--json'] if s.startswith('smoke_egress') else [])]) for s in scripts]
jobs += [(label,[sys.executable,'-B',ROOT/'tools'/script,*args]) for label,script,args in [
    ('schemas','validate-process-forge-schemas.py',[]),('public-cleanliness','validate-public-cleanliness.py',[]),
    ('checksums','validate-process-forge-checksums.py',['--check'])]]
passed,failed=[],[]
with ThreadPoolExecutor(max_workers=2) as pool:
    futures={pool.submit(command,'final-'+name,args,timeout=420):name for name,args in jobs}
    for future in as_completed(futures):
        name=futures[future]
        try:future.result();passed.append(name)
        except Exception as error:failed.append({'check':name,'error':str(error)[-600:]})
save('assurance-final-check-results.json',{'passed':sorted(passed),'failed':failed})
assert not failed,failed
baseline=json.loads((HERE/'baseline.json').read_text())
patterns=baseline['scope_patterns']
for filename in ['scope-amendment.json','assurance-scope-amendment.json']:
    patterns+=json.loads((HERE/filename).read_text())['additional_patterns']
spec=importlib.util.spec_from_file_location('inventory',ROOT/'tools/validate-process-forge-checksums.py')
inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
files={p.relative_to(ROOT).as_posix():p for p in inv.public_files(ROOT)+[ROOT/'checksums/processforge.sha256']}
changed=sorted(n for n,p in files.items() if baseline['public_sha256'].get(n)!=sha(p))
assert not(set(baseline['public_sha256'])-set(files))
assert all(any(fnmatch.fnmatchcase(n,p) for p in patterns) for n in changed),changed
for n in changed:
    if n.endswith('.py'):ast.parse((ROOT/n).read_text(encoding='utf-8-sig'))
hist=json.loads((HERE/'historical-preservation.json').read_text())
assert hist['doctor_before']==hist['doctor_after']
save('assurance-results.json',{'changed_files':changed,'source_sha256':{n:sha(files[n]) for n in changed},
    'passed':sorted(previous|set(passed)),'failed':[],'final_reruns':passed,'historical':'historical-preservation.json'})
print('PASS final source assurance',len(previous|set(passed)),'commands; scope',len(changed),'files',flush=True)
